import os
import logging
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .lead_source_provider import LeadSourceProvider
from services.shared.api_keys import get_org_api_key


logger = logging.getLogger(__name__)


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

    def _get_scrape_api_key(self, org_context: Dict[str, Any]) -> Optional[str]:
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

    def _build_scrape_query(self, request: Any) -> str:
        business_type = str(getattr(request, "business_type", "") or "").strip()
        location = getattr(request, "location", None)
        if isinstance(location, dict):
            location = location.get("text")
        location_text = str(location or "").strip()
        query_parts = [part for part in [business_type, location_text, "site:linkedin.com/in/"] if part]
        return " ".join(query_parts)

    def _parse_title(self, title: str) -> Dict[str, str]:
        cleaned_title = str(title or "").strip()
        if not cleaned_title:
            return {}

        if cleaned_title.endswith("| LinkedIn"):
            cleaned_title = cleaned_title[:-10].strip()

        parts = [part.strip() for part in cleaned_title.split(" - ") if str(part).strip()]
        parsed: Dict[str, str] = {}
        if parts:
            parsed["contact_name"] = parts[0]
        if len(parts) >= 2:
            parsed["job_title"] = parts[1]
        if len(parts) >= 3:
            parsed["business_name"] = parts[2]
        return parsed

    def _build_mock_leads(self, request: Any) -> List[Dict[str, Any]]:
        business_type = str(getattr(request, "business_type", "") or "").strip() or "Business Lead"
        location = getattr(request, "location", None)
        if isinstance(location, dict):
            location = location.get("text")
        location_text = str(location or "").strip() or "Sample City"

        return [
            {
                "contact_name": "Aarav Sharma",
                "business_name": "GrowthSpark",
                "job_title": business_type,
                "linkedin_url": "https://www.linkedin.com/in/aarav-sharma-growthspark",
                "source": "linkedin",
                "metadata": {
                    "title": f"Aarav Sharma - {business_type} - GrowthSpark | LinkedIn",
                    "mock": True,
                    "location": location_text,
                },
            },
            {
                "contact_name": "Priya Mehta",
                "business_name": "LeadBridge",
                "job_title": business_type,
                "linkedin_url": "https://www.linkedin.com/in/priya-mehta-leadbridge",
                "source": "linkedin",
                "metadata": {
                    "title": f"Priya Mehta - {business_type} - LeadBridge | LinkedIn",
                    "mock": True,
                    "location": location_text,
                },
            },
            {
                "contact_name": "Rohan Kulkarni",
                "business_name": "PipelineWorks",
                "job_title": business_type,
                "linkedin_url": "https://www.linkedin.com/in/rohan-kulkarni-pipelineworks",
                "source": "linkedin",
                "metadata": {
                    "title": f"Rohan Kulkarni - {business_type} - PipelineWorks | LinkedIn",
                    "mock": True,
                    "location": location_text,
                },
            },
        ]

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
        if org_context.get("request") is not None:
            return True
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
        api_key = self._get_scrape_api_key(org_context)
        if not api_key:
            logger.info("linkedin_scrape_mock_mode reason=no_api_key")
            return "success", self._build_mock_leads(request), ""

        query = self._build_scrape_query(request)
        if not query:
            return "success", [], ""

        try:
            max_results = max(1, min(int(getattr(request, "max_results", 10) or 10), 20))
        except Exception:
            max_results = 10

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(
                    "https://serpapi.com/search.json",
                    params={
                        "engine": "google",
                        "q": query,
                        "api_key": api_key,
                        "num": max_results,
                    },
                )
                if response.status_code != 200:
                    logger.warning("linkedin_scrape_bad_status status=%s", response.status_code)
                    return "success", [], ""

                payload = response.json() if response.content else {}
                if not isinstance(payload, dict):
                    return "success", [], ""

                organic_results = payload.get("organic_results", [])
                if not isinstance(organic_results, list) or not organic_results:
                    return "success", [], ""

                leads: List[Dict[str, Any]] = []
                seen_urls = set()

                for result in organic_results[:max_results]:
                    if not isinstance(result, dict):
                        continue

                    linkedin_url = str(result.get("link") or "").strip()
                    if "linkedin.com/in/" not in linkedin_url.lower():
                        continue
                    normalized_url = linkedin_url.lower()
                    if normalized_url in seen_urls:
                        continue
                    seen_urls.add(normalized_url)

                    original_title = str(result.get("title") or "").strip()
                    parsed_title = self._parse_title(original_title)
                    leads.append(
                        {
                            "contact_name": parsed_title.get("contact_name"),
                            "business_name": parsed_title.get("business_name"),
                            "job_title": parsed_title.get("job_title"),
                            "linkedin_url": linkedin_url,
                            "source": "linkedin",
                            "metadata": {
                                "title": original_title,
                            },
                        }
                    )

                return "success", leads, ""
        except Exception as exc:
            logger.exception("linkedin_scrape_failed error=%s", str(exc))
            return "success", [], ""
