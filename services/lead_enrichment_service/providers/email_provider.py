import os
import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from .lead_source_provider import LeadSourceProvider
from services.shared.api_keys import get_org_api_key


class EmailProvider(LeadSourceProvider):
    def provider_name(self) -> str:
        return "email"

    def _get_api_key(self, org_context: Dict[str, Any]) -> Optional[str]:
        db = org_context.get("db_session") or org_context.get("db")
        organization_id = org_context.get("organization_id") or org_context.get("org_id")

        if db is not None and organization_id:
            api_key, _ = get_org_api_key(db, organization_id, self.provider_name())
            if api_key:
                return api_key

        env_api_key = str(os.getenv("HUNTER_API_KEY") or "").strip()
        return env_api_key or None

    def _extract_domain(self, customer: Dict[str, Any]) -> str:
        website = str(customer.get("website") or "").strip()
        if website:
            candidate = website if "://" in website else f"https://{website}"
            parsed = urlparse(candidate)
            hostname = str(parsed.netloc or parsed.path or "").strip().lower()
            hostname = re.sub(r"^www\.", "", hostname)
            if hostname:
                return hostname

        business_name = str(
            customer.get("business_name")
            or customer.get("company_name")
            or ""
        ).strip().lower()
        if not business_name:
            return ""

        if "." in business_name and " " not in business_name:
            return re.sub(r"^www\.", "", business_name)

        slug = re.sub(r"[^a-z0-9]+", "", business_name)
        if not slug:
            return ""
        return f"{slug}.com"

    def validate_config(self, org_context: Dict[str, Any]) -> bool:
        return bool(self._get_api_key(org_context))

    async def enrich(self, customer: dict, org_context: dict) -> dict:
        api_key = self._get_api_key(org_context)
        if not api_key:
            return {}

        domain = self._extract_domain(customer)
        if not domain:
            return {}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    "https://api.hunter.io/v2/domain-search",
                    params={
                        "domain": domain,
                        "api_key": api_key,
                    },
                )
                if response.status_code != 200:
                    return {}

                payload = response.json() if response.content else {}
                data = payload.get("data", {}) if isinstance(payload, dict) else {}
                emails = data.get("emails", []) if isinstance(data, dict) else []
                if not emails or not isinstance(emails, list):
                    return {}

                first_email = emails[0] if isinstance(emails[0], dict) else {}
                email_value = str(first_email.get("value") or "").strip()
                if not email_value:
                    return {}

                return {
                    "email": email_value,
                    "email_source": "hunter",
                }
        except Exception:
            return {}

    async def scrape(
        self,
        request: Any,
        org_context: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        return "error", [], "Email source is not configured for lead scraping."
