from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urlparse


PROJECT_ROOT = Path(__file__).resolve().parents[3]
SHARED_ENGINE_PATH = PROJECT_ROOT / "lead-scraper-extension" / "shared_scraper_engine.js"
NEXT_BUTTON_LABELS = ("next", "next page", "load more", "more", "older", ">>", ">", "->")
BLOCKED_DOMAIN_TOKENS = (
    "h1ad.com",
    "doubleclick.net",
    "googlesyndication.com",
    "adservice.google.com",
    "doubleclick",
    "googlesyndication",
    "adservice",
    "h1ad",
)


def _normalize_url(url: str) -> str:
    normalized = str(url or "").strip()
    if not normalized:
        raise ValueError("website_url is required.")
    if not normalized.startswith(("http://", "https://")):
        normalized = f"https://{normalized}"

    parsed = urlparse(normalized)
    hostname = str(parsed.hostname or "").strip()
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or " " in parsed.netloc
        or "." not in hostname
    ):
        raise ValueError(f"Invalid website_url: {url}")
    return normalized


def _shared_engine_source() -> str:
    if not SHARED_ENGINE_PATH.exists():
        raise RuntimeError(f"Shared scraper engine not found at {SHARED_ENGINE_PATH}")
    return SHARED_ENGINE_PATH.read_text(encoding="utf-8")


def _is_blocked_url(url: str) -> bool:
    normalized = str(url or "").strip().lower()
    return any(token in normalized for token in BLOCKED_DOMAIN_TOKENS)


def _is_same_domain_or_subdomain(original_domain: str, current_url: str) -> bool:
    try:
        current_domain = str(urlparse(current_url).netloc or "").strip().lower()
    except Exception:
        return False

    original = str(original_domain or "").strip().lower()
    if not original or not current_domain:
        return False
    return current_domain == original or current_domain.endswith(f".{original}")


async def _wait_for_render(page: Any) -> None:
    print(f"[SCRAPER] Waiting for DOM content. Current URL: {page.url}")
    await page.wait_for_load_state("domcontentloaded", timeout=45000)
    print(f"[SCRAPER] DOM content loaded. Current URL: {page.url}")
    try:
        print(f"[SCRAPER] Waiting for networkidle. Current URL: {page.url}")
        await page.wait_for_load_state("networkidle", timeout=5000)
        print(f"[SCRAPER] networkidle reached. Current URL: {page.url}")
    except Exception as exc:
        print(f"[SCRAPER] networkidle wait failed, using fallback wait. URL: {page.url}. Error: {str(exc)}")
        await page.wait_for_timeout(5000)
        print(f"[SCRAPER] Fallback wait complete. Current URL: {page.url}")
    await page.wait_for_timeout(1200)
    print(f"[SCRAPER] Additional render wait complete. Current URL: {page.url}")


async def _scroll_page(page: Any) -> None:
    await _scroll_page_with_retries(page)


async def _scroll_page_with_retries(page: Any, retries: int = 2) -> None:
    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            print(f"[SCRAPER] Starting scroll attempt {attempt + 1}/{retries + 1}. URL: {page.url}")
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            print(f"[SCRAPER] Page stable before scroll. URL: {page.url}")

            await page.evaluate(
                """
                async () => {
                    const delay = (ms) => new Promise(r => setTimeout(r, ms));
                    let lastHeight = 0;

                    for (let i = 0; i < 6; i++) {
                        window.scrollTo(0, document.body.scrollHeight);
                        await delay(700);

                        let newHeight = document.body.scrollHeight;
                        if (newHeight === lastHeight) break;
                        lastHeight = newHeight;
                    }

                    window.scrollTo(0, 0);
                }
                """
            )

            await page.wait_for_timeout(1000)
            print(f"[SCRAPER] Scroll successful. URL: {page.url}")
            return

        except Exception as e:
            last_error = e
            print(f"[SCRAPER ERROR] Scroll failed attempt {attempt + 1}: {str(e)}")
            print(f"[SCRAPER ERROR] URL during failure: {page.url}")

            if attempt >= retries:
                raise

            print("[SCRAPER] Waiting before retrying scroll...")
            await page.wait_for_timeout(2000)

            try:
                await page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

    if last_error:
        raise last_error


async def _extract_payload(page: Any, retries: int = 2) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=30000)
            print(f"[SCRAPER] Preparing to evaluate extractor. Attempt {attempt + 1}/{retries + 1}. Current URL: {page.url}")
            payload = await page.evaluate(
                """
                () => {
                    if (!window.__MAI_SHARED_SCRAPER__ || typeof window.__MAI_SHARED_SCRAPER__.extractPayload !== 'function') {
                        throw new Error('Shared scraper engine is not available on the page.');
                    }
                    return window.__MAI_SHARED_SCRAPER__.extractPayload(document);
                }
                """
            )
            print(f"[SCRAPER] Evaluate succeeded. Current URL: {page.url}")
            if not isinstance(payload, dict):
                raise RuntimeError("The page extractor returned an invalid payload.")
            return payload
        except Exception as exc:
            last_error = exc
            print(f"[SCRAPER ERROR] Evaluate failed: {str(exc)}")
            print(f"[SCRAPER ERROR] Current URL: {page.url}")
            print("[SCRAPER ERROR] Traceback:")
            print(traceback.format_exc())
            if attempt >= retries:
                raise
            print(f"[SCRAPER] Retrying evaluate after stability wait. Next attempt: {attempt + 2}/{retries + 1}")
            await page.wait_for_timeout(2000)

    if last_error:
        raise last_error
    raise RuntimeError("Evaluate failed without a captured exception.")


def _merge_unique_dicts(existing: List[Dict[str, Any]], items: List[Dict[str, Any]], keys: Set[str]) -> None:
    seen = set()
    for item in existing:
        signature = json.dumps({key: item.get(key) for key in keys}, sort_keys=True, default=str)
        seen.add(signature)
    for item in items:
        signature = json.dumps({key: item.get(key) for key in keys}, sort_keys=True, default=str)
        if signature in seen:
            continue
        seen.add(signature)
        existing.append(item)


def _merge_payloads(base: Optional[Dict[str, Any]], incoming: Dict[str, Any]) -> Dict[str, Any]:
    if not base:
        merged = dict(incoming)
        merged["pagination"] = {
            "pages_scraped": 1,
        }
        return merged

    _merge_unique_dicts(base.setdefault("links", []), incoming.get("links", []), {"href", "text"})
    _merge_unique_dicts(base.setdefault("contacts", []), incoming.get("contacts", []), {"email", "phone"})

    existing_headings = {str(item).strip().lower() for item in base.setdefault("headings", [])}
    for heading in incoming.get("headings", []):
        normalized = str(heading or "").strip()
        if not normalized or normalized.lower() in existing_headings:
            continue
        existing_headings.add(normalized.lower())
        base["headings"].append(normalized)

    _merge_unique_dicts(base.setdefault("tables", []), incoming.get("tables", []), {"kind", "headers", "rows"})
    pagination = base.setdefault("pagination", {})
    pagination["pages_scraped"] = int(pagination.get("pages_scraped", 1)) + 1
    return base


async def _click_next_page(page: Any) -> bool:
    print(f"[SCRAPER] Looking for next page control. Current URL: {page.url}")
    return bool(
        await page.evaluate(
            f"""
            async () => {{
                const labels = {json.dumps(NEXT_BUTTON_LABELS)};
                const elements = Array.from(document.querySelectorAll('a[href], button, [role="button"]'));
                const isVisible = (el) => {{
                    const style = window.getComputedStyle(el);
                    const rect = el.getBoundingClientRect();
                    return style && style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
                }};
                const candidates = elements.filter((el) => isVisible(el)).map((el) => {{
                    const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().toLowerCase();
                    const rel = (el.getAttribute('rel') || '').trim().toLowerCase();
                    const cls = (el.className || '').toString().toLowerCase();
                    const score = labels.some((label) => text === label || text.includes(label)) || rel.includes('next') || cls.includes('next');
                    return {{ el, score }};
                }}).filter((item) => item.score);
                if (!candidates.length) {{
                    return false;
                }}
                candidates[0].el.click();
                return true;
            }}
            """
        )
    )


async def _configure_request_blocking(page: Any) -> None:
    async def _route_handler(route: Any) -> None:
        request_url = str(route.request.url or "")
        if _is_blocked_url(request_url):
            print(f"[SCRAPER] Blocked ad/tracker request: {request_url}")
            await route.abort()
            return
        await route.continue_()

    await page.route("**/*", _route_handler)


async def scrape_url_with_playwright(url: str, max_pages: int = 5) -> Dict[str, Any]:
    normalized_url = _normalize_url(url)
    original_domain = str(urlparse(normalized_url).netloc or "").strip().lower()
    shared_engine = _shared_engine_source()
    merged_payload: Optional[Dict[str, Any]] = None
    page_signatures: Set[str] = set()

    try:
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Install dependencies, then run: playwright install"
            ) from exc

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                page = await browser.new_page(viewport={"width": 1440, "height": 2200})
                await page.add_init_script(shared_engine)
                await _configure_request_blocking(page)
                if _is_blocked_url(normalized_url):
                    print(f"[SCRAPER WARNING] Skipping blocked target URL before navigation: {normalized_url}")
                    return {}
                print(f"[SCRAPER] Navigating to: {normalized_url}")
                try:
                    await page.goto(normalized_url, wait_until="domcontentloaded", timeout=30000)
                except Exception as exc:
                    print(f"[SCRAPER WARNING] goto timeout, continuing with partial load. URL: {normalized_url}. Error: {str(exc)}")
                print(f"[SCRAPER] page.goto() completed. Current URL after load: {page.url}")
                print(f"[SCRAPER] Final URL after redirects: {page.url}")
                if _is_blocked_url(page.url):
                    print(f"[SCRAPER WARNING] Skipping blocked redirect URL: {page.url}")
                    return {}
                if not _is_same_domain_or_subdomain(original_domain, page.url):
                    print(f"[SCRAPER WARNING] Redirected to external domain: {page.url}")
                    return {}
                await page.wait_for_timeout(3000)
                print(f"[SCRAPER] Post-goto stability wait complete. Current URL: {page.url}")
                try:
                    await page.wait_for_load_state("networkidle", timeout=5000)
                    print(f"[SCRAPER] Post-goto networkidle confirmed. Current URL: {page.url}")
                except Exception as exc:
                    print(f"[SCRAPER] Post-goto networkidle failed, using fallback wait. URL: {page.url}. Error: {str(exc)}")
                    await page.wait_for_timeout(5000)
                    print(f"[SCRAPER] Post-goto fallback wait complete. Current URL: {page.url}")

                for page_index in range(max_pages):
                    print(f"[SCRAPER] Starting extraction for page index {page_index}. Current URL: {page.url}")
                    await _wait_for_render(page)
                    await _scroll_page(page)
                    payload = await _extract_payload(page)

                    signature = json.dumps(
                        {
                            "title": payload.get("page_title"),
                            "headings": payload.get("headings", [])[:10],
                            "links": payload.get("links", [])[:20],
                            "tables": payload.get("tables", [])[:5],
                        },
                        sort_keys=True,
                        default=str,
                    )
                    if signature in page_signatures:
                        break
                    page_signatures.add(signature)
                    merged_payload = _merge_payloads(merged_payload, payload)

                    if page_index >= max_pages - 1:
                        break

                    clicked = await _click_next_page(page)
                    if not clicked:
                        print(f"[SCRAPER] No next page control found. Stopping pagination at URL: {page.url}")
                        break

                    try:
                        print(f"[SCRAPER] Waiting for next-page navigation to settle. Current URL: {page.url}")
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        print(f"[SCRAPER] Next-page navigation settled. Current URL: {page.url}")
                    except Exception as exc:
                        print(f"[SCRAPER] Next-page networkidle failed, using fallback wait. URL: {page.url}. Error: {str(exc)}")
                        await page.wait_for_timeout(5000)
                        print(f"[SCRAPER] Next-page fallback wait complete. Current URL: {page.url}")

                await browser.close()
        except PlaywrightTimeoutError as exc:
            print("[SCRAPER ERROR] Timeout during Playwright execution:")
            print(traceback.format_exc())
            raise TimeoutError(f"Timed out while loading or rendering {normalized_url}.") from exc
    except ValueError:
        raise
    except TimeoutError:
        raise
    except RuntimeError:
        raise
    except Exception as exc:
        print(f"[SCRAPER ERROR] Unexpected scraper failure for URL {normalized_url}: {str(exc)}")
        print(traceback.format_exc())
        raise RuntimeError(f"Playwright scraping failed for {normalized_url}: {str(exc)}") from exc

    if not merged_payload:
        raise RuntimeError("No data could be extracted from the target page.")

    if not any(merged_payload.get(key) for key in ("tables", "links", "headings", "contacts")):
        raise RuntimeError("The target page rendered, but no extractable content was found.")

    return merged_payload
