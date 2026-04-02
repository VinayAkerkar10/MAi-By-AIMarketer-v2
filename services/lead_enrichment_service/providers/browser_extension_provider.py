from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse
import json
import logging
import os
import re

from .lead_source_provider import LeadSourceProvider


logger = logging.getLogger(__name__)
EMAIL_REGEX = re.compile(r"[\w.\-+%]+@[\w.\-]+\.[A-Za-z]{2,}")
PHONE_REGEX = re.compile(r"\+?\d[\d\s().\-]{6,}\d")
INVALID_LINK_PREFIXES = ("javascript:", "#", "mailto:", "tel:")


class BrowserExtensionProvider(LeadSourceProvider):
    def provider_name(self) -> str:
        return "browser_extension"

    def validate_config(self, org_context: Dict[str, Any]) -> bool:
        request = org_context.get("request")
        if request is None:
            return False
        payload = getattr(request, "extension_payload", None)
        return isinstance(payload, dict) and bool(payload)

    async def scrape(
        self,
        request: Any,
        org_context: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        extension_payload = getattr(request, "extension_payload", None)
        website_url = _normalize_text(getattr(request, "website_url", None))

        payload = extension_payload if isinstance(extension_payload, dict) else {}
        if website_url and not payload.get("website_url"):
            payload["website_url"] = website_url

        leads = extract_leads_from_payload(payload)
        logger.info("[Backend] Clean leads extracted: %s", len(leads))
        if not leads:
            return "error", [], "Extension payload did not contain any usable lead data."

        enhanced_leads = await enhance_leads_with_ai(payload, leads)
        return "success", enhanced_leads, ""


def extract_leads_from_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    website_url = _normalize_url(payload.get("website_url"))
    payload_links = payload.get("links", []) if isinstance(payload.get("links"), list) else []
    payload_contacts = payload.get("contacts", []) if isinstance(payload.get("contacts"), list) else []
    payload_headings = payload.get("headings", []) if isinstance(payload.get("headings"), list) else []
    payload_tables = payload.get("tables", []) if isinstance(payload.get("tables"), list) else []

    filtered_links: List[Dict[str, str]] = []
    seen_link_urls = set()
    for link in payload_links:
        if not isinstance(link, dict):
            continue
        href = _normalize_url(link.get("href"))
        if not href:
            continue
        href_lower = href.lower()
        if href_lower.startswith(INVALID_LINK_PREFIXES):
            continue
        if href in seen_link_urls:
            continue
        seen_link_urls.add(href)
        filtered_links.append({
            "href": href,
            "text": _normalize_text(link.get("text")) or "",
        })

    headings = [
        _normalize_heading(heading)
        for heading in payload_headings
        if _normalize_heading(heading)
    ][:10]

    contact_emails = [
        _find_email(contact.get("email") if isinstance(contact, dict) else None)
        for contact in payload_contacts
    ]
    contact_phones = [
        _find_phone(contact.get("phone") if isinstance(contact, dict) else None)
        for contact in payload_contacts
    ]

    leads: List[Dict[str, Any]] = []
    used_heading_names = set()

    for link in filtered_links:
        domain = _extract_domain(link.get("href"))
        if not domain:
            continue
        name = _guess_business_name(link.get("text"), domain, headings)
        used_heading_names.add(name.lower())
        leads.append(
            _build_lead(
                name=name,
                website=link.get("href"),
                email=None,
                phone=None,
                raw_payload=link,
                origin="links",
            )
        )

    for heading in headings:
        if heading.lower() in used_heading_names:
            continue
        if _looks_like_noise(heading):
            continue
        leads.append(
            _build_lead(
                name=heading,
                website=website_url,
                email=None,
                phone=None,
                raw_payload={"heading": heading},
                origin="headings",
            )
        )

    for idx, contact in enumerate(payload_contacts):
        if not isinstance(contact, dict):
            continue
        email = contact_emails[idx] if idx < len(contact_emails) else None
        phone = contact_phones[idx] if idx < len(contact_phones) else None
        if not email and not phone:
            continue
        leads.append(
            _build_lead(
                name=_guess_business_name(None, website_url, headings),
                website=website_url,
                email=email,
                phone=phone,
                raw_payload=contact,
                origin="contacts",
            )
        )

    for table in payload_tables:
        if not isinstance(table, dict):
            continue
        rows = table.get("rows", [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            row_name = _guess_business_name_from_row(row)
            row_email = _find_email(" ".join(str(v) for v in row.values()))
            row_phone = _find_phone(" ".join(str(v) for v in row.values()))
            row_website = _normalize_url(row.get("website") or row.get("url") or website_url)
            if not row_name and not row_email and not row_phone and not row_website:
                continue
            leads.append(
                _build_lead(
                    name=row_name or _guess_business_name(None, row_website, headings),
                    website=row_website,
                    email=row_email,
                    phone=row_phone,
                    raw_payload=row,
                    origin="tables",
                )
            )

    deduped: Dict[str, Dict[str, Any]] = {}
    for lead in leads:
        website_key = _extract_domain(lead.get("website"))
        email_key = _normalize_text(lead.get("email"))
        if email_key:
            deduped[f"email::{email_key.lower()}"] = lead
            continue
        if website_key:
            deduped[f"website::{website_key.lower()}"] = lead
            continue
        deduped[f"name::{str(lead.get('business_name') or '').lower()}"] = lead

    clean_leads = [lead for lead in deduped.values() if not _looks_like_noise(lead.get("business_name"))]
    return clean_leads


async def enhance_leads_with_ai(payload: Dict[str, Any], leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not leads:
        return leads

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return leads

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=openai_api_key,
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
        model = os.getenv("OPENAI_MODEL", "gpt-4")
        prompt = (
            "Clean and normalize business leads extracted from browser payloads. "
            "Return JSON only with shape: {\"leads\": [{\"name\": str, \"website\": str|null, \"email\": str|null, \"phone\": str|null}]}. "
            "Remove obvious junk rows, infer better business names when possible, and keep only realistic business leads.\n\n"
            f"Payload summary: {json.dumps({'website_url': payload.get('website_url'), 'headings': payload.get('headings', [])[:10]}, ensure_ascii=True)}\n"
            f"Leads: {json.dumps([{k: lead.get(k) for k in ['business_name', 'website', 'email', 'phone']} for lead in leads[:25]], ensure_ascii=True)}"
        )
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You clean business lead data and return strict JSON."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1200,
        )
        content = response.choices[0].message.content if response.choices else ""
        parsed = json.loads(content or "{}")
        ai_leads = parsed.get("leads", []) if isinstance(parsed, dict) else []
        normalized_ai_leads = []
        for lead in ai_leads:
            if not isinstance(lead, dict):
                continue
            normalized_ai_leads.append(
                _build_lead(
                    name=_normalize_text(lead.get("name")) or "Unknown",
                    website=_normalize_url(lead.get("website")),
                    email=_find_email(lead.get("email")),
                    phone=_find_phone(lead.get("phone")),
                    raw_payload=lead,
                    origin="ai_enhanced",
                )
            )
        if normalized_ai_leads:
            logger.info("[AI] Leads enhanced")
            return normalized_ai_leads
    except Exception as exc:
        logger.warning("[AI] Lead enhancement failed, using rule-based extraction: %s", exc)

    return leads


def _build_lead(
    name: Optional[str],
    website: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    raw_payload: Dict[str, Any],
    origin: str,
) -> Dict[str, Any]:
    clean_name = _normalize_text(name) or "Unknown"
    return {
        "business_name": clean_name,
        "contact_name": None,
        "name": clean_name,
        "website": _normalize_url(website),
        "email": _find_email(email),
        "phone": _find_phone(phone),
        "address": None,
        "source": "browser_extension",
        "category": origin,
        "scraped_at": datetime.utcnow().isoformat(),
        "metadata": {
            "origin": origin,
            "raw_payload": raw_payload,
        },
        "raw_payload": raw_payload,
    }


def _guess_business_name(link_text: Optional[str], website: Optional[str], headings: List[str]) -> str:
    clean_text = _normalize_heading(link_text)
    if clean_text and not _looks_like_noise(clean_text):
        return clean_text
    for heading in headings:
        if not _looks_like_noise(heading):
            return heading
    domain = _extract_domain(website)
    if domain:
        return domain.split(".")[0].replace("-", " ").replace("_", " ").title()
    return "Unknown"


def _guess_business_name_from_row(row: Dict[str, Any]) -> Optional[str]:
    for key in ["company", "company_name", "business", "business_name", "name", "organization"]:
        value = _normalize_heading(row.get(key))
        if value and not _looks_like_noise(value):
            return value
    for value in row.values():
        clean = _normalize_heading(value)
        if clean and not _looks_like_noise(clean):
            return clean
    return None


def _extract_domain(url: Any) -> Optional[str]:
    normalized = _normalize_url(url)
    if not normalized:
        return None
    try:
        parsed = urlparse(normalized)
        return (parsed.netloc or parsed.path).replace("www.", "").strip() or None
    except Exception:
        return None


def _find_email(value: Any) -> Optional[str]:
    text = _normalize_text(value)
    if not text:
        return None
    match = EMAIL_REGEX.search(text)
    return match.group(0).lower() if match else None


def _find_phone(value: Any) -> Optional[str]:
    text = _normalize_text(value)
    if not text:
        return None
    match = PHONE_REGEX.search(text)
    return match.group(0).strip() if match else None


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_heading(value: Any) -> Optional[str]:
    text = _normalize_text(value)
    if not text:
        return None
    compact = " ".join(text.split())
    return compact[:120] if compact else None


def _normalize_url(value: Any) -> Optional[str]:
    text = _normalize_text(value)
    if not text:
        return None
    lower = text.lower()
    if lower.startswith(INVALID_LINK_PREFIXES):
        return None
    if text.startswith(("http://", "https://")):
        return text
    if "." in text and " " not in text:
        return f"https://{text.lstrip('/')}"
    return None


def _looks_like_noise(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return True
    noisy_terms = {"home", "about", "contact", "login", "sign up", "sign in", "read more", "learn more", "menu"}
    return text in noisy_terms or len(text) < 3
