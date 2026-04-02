from typing import Any, Dict, List, Tuple

from services.lead_enrichment_service.scrapers.playwright_scraper import scrape_url_with_playwright

from .browser_extension_provider import extract_leads_from_payload
from .lead_source_provider import LeadSourceProvider


class DirectUrlProvider(LeadSourceProvider):
    def provider_name(self) -> str:
        return "direct_url"

    def validate_config(self, org_context: Dict[str, Any]) -> bool:
        request = org_context.get("request")
        if request is None:
            return False
        return bool(str(getattr(request, "website_url", None) or "").strip())

    async def scrape(
        self,
        request: Any,
        org_context: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        website_url = str(getattr(request, "website_url", None) or "").strip()
        if not website_url:
            return "error", [], "A valid website_url is required for direct URL scraping."

        try:
            payload = await scrape_url_with_playwright(
                website_url,
                max_pages=max(1, min(int(getattr(request, "max_results", 5) or 5), 10)),
            )
        except ValueError as exc:
            return "error", [], str(exc)
        except TimeoutError as exc:
            return "error", [], str(exc)
        except RuntimeError as exc:
            return "error", [], str(exc)
        except Exception as exc:
            return "error", [], f"Direct URL scraping failed: {str(exc)}"

        leads = extract_leads_from_payload(payload)
        if not leads:
            return "error", [], "The rendered page did not contain any usable lead data."

        for lead in leads:
            if isinstance(lead, dict):
                lead["source"] = "direct_url"
                metadata = lead.get("metadata")
                if isinstance(metadata, dict):
                    metadata["scrape_mode"] = "direct_url"

        return "success", leads, ""
