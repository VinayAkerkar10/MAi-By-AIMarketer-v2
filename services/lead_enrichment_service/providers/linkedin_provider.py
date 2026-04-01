import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .lead_source_provider import LeadSourceProvider
from services.shared.api_keys import get_org_api_key


class LinkedInProvider(LeadSourceProvider):
    def provider_name(self) -> str:
        return "linkedin"

    def _get_api_key(self, org_context: Dict[str, Any]) -> Optional[str]:
        db = org_context.get("db_session") or org_context.get("db")
        organization_id = org_context.get("organization_id") or org_context.get("org_id")

        if db is not None and organization_id:
            api_key, _ = get_org_api_key(db, organization_id, self.provider_name())
            if api_key:
                return api_key

        for env_key in ("SERPAPI_API_KEY", "LINKEDIN_API_KEY"):
            env_value = str(os.getenv(env_key) or "").strip()
            if env_value:
                return env_value
        return None

    def _build_search_query(self, customer: Dict[str, Any]) -> str:
        name = str(customer.get("name") or "").strip()
        company = str(customer.get("business_name") or customer.get("company_name") or "").strip()
        if company:
            return f"{name} {company} linkedin"
        return f"{name} linkedin"

    def _extract_linkedin_url(self, payload: Dict[str, Any]) -> Optional[str]:
        organic_results = payload.get("organic_results", []) if isinstance(payload, dict) else []
        if not isinstance(organic_results, list):
            return None

        for result in organic_results:
            if not isinstance(result, dict):
                continue

            candidate_urls = [
                result.get("link"),
                result.get("displayed_link"),
            ]
            for candidate_url in candidate_urls:
                url = str(candidate_url or "").strip()
                if "linkedin.com/in/" in url.lower():
                    return url
        return None

    def _extract_job_title(self, payload: Dict[str, Any], linkedin_url: str) -> Optional[str]:
        organic_results = payload.get("organic_results", []) if isinstance(payload, dict) else []
        if not isinstance(organic_results, list):
            return None

        normalized_target = str(linkedin_url or "").strip().lower()
        for result in organic_results:
            if not isinstance(result, dict):
                continue

            link = str(result.get("link") or "").strip().lower()
            if normalized_target and link != normalized_target:
                continue

            title = str(result.get("title") or "").strip()
            if not title:
                continue

            title_parts = [part.strip() for part in title.split(" - ") if str(part).strip()]
            if len(title_parts) >= 2:
                return title_parts[1]
        return None

    def validate_config(self, org_context: Dict[str, Any]) -> bool:
        return bool(self._get_api_key(org_context))

    async def enrich(self, customer: dict, org_context: dict) -> dict:
        name = str(customer.get("name") or "").strip()
        if not name:
            return {}

        api_key = self._get_api_key(org_context)
        if not api_key:
            return {}

        query = self._build_search_query(customer)

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    "https://serpapi.com/search.json",
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": api_key,
                        "num": 10,
                    },
                )
                if response.status_code != 200:
                    return {}

                payload = response.json() if response.content else {}
                if not isinstance(payload, dict):
                    return {}

                linkedin_url = self._extract_linkedin_url(payload)
                if not linkedin_url:
                    return {}

                normalized = {
                    "linkedin_url": linkedin_url,
                }

                job_title = self._extract_job_title(payload, linkedin_url)
                if job_title:
                    normalized["job_title"] = job_title

                return normalized
        except Exception:
            return {}

    async def scrape(
        self,
        request: Any,
        org_context: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        return "error", [], "Linkedin source is not configured."
