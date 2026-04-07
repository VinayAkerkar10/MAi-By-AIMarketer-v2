import asyncio
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .lead_source_provider import LeadSourceProvider
from services.shared.api_keys import get_org_api_key


logger = logging.getLogger(__name__)


class GoogleMapsProvider(LeadSourceProvider):
    TEXT_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"

    def provider_name(self) -> str:
        return "google_maps"

    def _get_api_key(self, org_context: Dict[str, Any]) -> Optional[str]:
        db = org_context.get("db_session") or org_context.get("db")
        organization_id = org_context.get("organization_id") or org_context.get("org_id")

        if db is not None and organization_id:
            api_key, _ = get_org_api_key(db, organization_id, self.provider_name())
            if api_key:
                return api_key

        env_api_key = str(os.getenv("GOOGLE_MAPS_API_KEY") or "").strip()
        return env_api_key or None

    def validate_config(self, org_context: Dict[str, Any]) -> bool:
        # Allow scrape() to decide how to handle missing keys so the lead pipeline
        # can return an empty dataset instead of surfacing a provider error.
        if org_context.get("request") is not None:
            return True
        return bool(self._get_api_key(org_context))

    def _build_text_search_query(self, request: Any) -> str:
        business_type = str(getattr(request, "business_type", "") or "").strip()
        location = getattr(request, "location", None)
        if isinstance(location, dict):
            location = location.get("text")
        location_text = str(location or "").strip()

        if business_type and location_text:
            return f"{business_type} in {location_text}"
        return business_type or location_text

    def _build_mock_leads(self, request: Any) -> List[Dict[str, Any]]:
        business_type = str(getattr(request, "business_type", "") or "").strip() or "Business"
        location = getattr(request, "location", None)
        if isinstance(location, dict):
            location = location.get("text")
        location_text = str(location or "").strip() or "Sample City"
        business_slug = business_type.lower().replace(" ", "-")

        return [
            {
                "business_name": f"{business_type} Hub",
                "address": f"101 Market Street, {location_text}",
                "phone": "+1 555-0101",
                "website": f"https://www.{business_slug}hub.example",
                "source": "google_maps",
                "metadata": {
                    "place_id": f"mock-{business_slug}-1",
                    "rating": 4.6,
                    "user_ratings_total": 128,
                    "types": ["point_of_interest", "establishment"],
                    "mock": True,
                },
            },
            {
                "business_name": f"{business_type} Partners",
                "address": f"202 Commerce Avenue, {location_text}",
                "phone": "+1 555-0102",
                "website": f"https://www.{business_slug}partners.example",
                "source": "google_maps",
                "metadata": {
                    "place_id": f"mock-{business_slug}-2",
                    "rating": 4.4,
                    "user_ratings_total": 86,
                    "types": ["professional_service", "establishment"],
                    "mock": True,
                },
            },
            {
                "business_name": f"{business_type} Collective",
                "address": f"303 Growth Plaza, {location_text}",
                "phone": "+1 555-0103",
                "website": f"https://www.{business_slug}collective.example",
                "source": "google_maps",
                "metadata": {
                    "place_id": f"mock-{business_slug}-3",
                    "rating": 4.2,
                    "user_ratings_total": 54,
                    "types": ["store", "point_of_interest", "establishment"],
                    "mock": True,
                },
            },
        ]

    async def _text_search_places(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        query: str,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        if not api_key or not query:
            return []

        collected: List[Dict[str, Any]] = []
        next_page_token: Optional[str] = None
        seen_place_ids = set()

        while len(collected) < max_results:
            params = {
                "query": query,
                "key": api_key,
            }
            if next_page_token:
                # Google Places may take a short time before the token is usable.
                await asyncio.sleep(2)
                params = {
                    "pagetoken": next_page_token,
                    "key": api_key,
                }

            try:
                response = await client.get(self.TEXT_SEARCH_URL, params=params)
            except Exception as exc:
                logger.warning("google_maps_text_search_request_failed error=%s", str(exc))
                break

            if response.status_code != 200:
                logger.warning("google_maps_text_search_bad_status status=%s", response.status_code)
                break

            payload = response.json() if response.content else {}
            if not isinstance(payload, dict):
                break

            api_status = str(payload.get("status") or "").strip().upper()
            if api_status not in {"OK", "ZERO_RESULTS"}:
                logger.warning("google_maps_text_search_api_status status=%s", api_status or "UNKNOWN")
                break

            results = payload.get("results", [])
            if not isinstance(results, list) or not results:
                break

            for result in results:
                if not isinstance(result, dict):
                    continue
                place_id = str(result.get("place_id") or "").strip()
                if place_id and place_id in seen_place_ids:
                    continue
                if place_id:
                    seen_place_ids.add(place_id)
                collected.append(result)
                if len(collected) >= max_results:
                    break

            next_page_token = str(payload.get("next_page_token") or "").strip() or None
            if not next_page_token:
                break

        return collected[:max_results]

    async def _fetch_place_details(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        place_id: str,
    ) -> Dict[str, Any]:
        if not api_key or not place_id:
            return {}

        try:
            response = await client.get(
                self.DETAILS_URL,
                params={
                    "place_id": place_id,
                    "fields": "name,formatted_address,international_phone_number,website,geometry,place_id,rating,user_ratings_total,types",
                    "key": api_key,
                },
            )
        except Exception as exc:
            logger.warning("google_maps_details_request_failed place_id=%s error=%s", place_id, str(exc))
            return {}

        if response.status_code != 200:
            logger.warning("google_maps_details_bad_status place_id=%s status=%s", place_id, response.status_code)
            return {}

        payload = response.json() if response.content else {}
        if not isinstance(payload, dict):
            return {}

        api_status = str(payload.get("status") or "").strip().upper()
        if api_status != "OK":
            if api_status and api_status != "ZERO_RESULTS":
                logger.warning("google_maps_details_api_status place_id=%s status=%s", place_id, api_status)
            return {}

        result = payload.get("result")
        return result if isinstance(result, dict) else {}

    def _build_raw_lead(
        self,
        place_result: Dict[str, Any],
        details_result: Dict[str, Any],
    ) -> Dict[str, Any]:
        source = details_result if isinstance(details_result, dict) and details_result else place_result
        geometry = source.get("geometry", {}) if isinstance(source, dict) else {}
        location = geometry.get("location", {}) if isinstance(geometry, dict) else {}
        place_id = str(source.get("place_id") or place_result.get("place_id") or "").strip()

        metadata: Dict[str, Any] = {}
        if place_id:
            metadata["place_id"] = place_id
        if isinstance(location, dict) and location.get("lat") is not None and location.get("lng") is not None:
            metadata["geometry"] = {
                "lat": location.get("lat"),
                "lng": location.get("lng"),
            }
        rating = source.get("rating")
        if rating is not None:
            metadata["rating"] = rating
        user_ratings_total = source.get("user_ratings_total")
        if user_ratings_total is not None:
            metadata["user_ratings_total"] = user_ratings_total
        types = source.get("types")
        if isinstance(types, list) and types:
            metadata["types"] = types

        lead = {
            "business_name": source.get("name") or place_result.get("name"),
            "address": source.get("formatted_address") or place_result.get("formatted_address"),
            "phone": source.get("international_phone_number"),
            "website": source.get("website"),
            "source": "google_maps",
            "metadata": metadata,
        }
        return {key: value for key, value in lead.items() if value not in (None, "", [], {})}

    async def enrich(self, customer: dict, org_context: dict) -> dict:
        company = (
            str(customer.get("business_name") or "").strip()
            or str(customer.get("company_name") or "").strip()
        )
        phone = str(customer.get("phone") or "").strip()
        if not company:
            return {}

        api_key = self._get_api_key(org_context)
        if not api_key:
            return {}

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                find_response = await client.get(
                    "https://maps.googleapis.com/maps/api/place/findplacefromtext/json",
                    params={
                        "input": company,
                        "inputtype": "textquery",
                        "fields": "name,formatted_address,international_phone_number,website,place_id",
                        "key": api_key,
                    },
                )
                if find_response.status_code != 200:
                    return {}

                find_payload = find_response.json() if find_response.content else {}
                candidates = find_payload.get("candidates", []) if isinstance(find_payload, dict) else []
                if not candidates:
                    return {}

                candidate = candidates[0] if isinstance(candidates[0], dict) else {}
                place_id = str(candidate.get("place_id") or "").strip()

                details_payload: Dict[str, Any] = {}
                if place_id:
                    details_response = await client.get(
                        "https://maps.googleapis.com/maps/api/place/details/json",
                        params={
                            "place_id": place_id,
                            "fields": "name,formatted_address,international_phone_number,website,geometry,place_id",
                            "key": api_key,
                        },
                    )
                    if details_response.status_code == 200:
                        parsed_details = details_response.json() if details_response.content else {}
                        if isinstance(parsed_details, dict):
                            details_payload = parsed_details.get("result", {}) if isinstance(parsed_details.get("result"), dict) else {}

                source = details_payload or candidate
                geometry = details_payload.get("geometry", {}) if isinstance(details_payload, dict) else {}
                location = geometry.get("location", {}) if isinstance(geometry, dict) else {}

                normalized = {
                    "business_name": source.get("name") or company,
                    "address": source.get("formatted_address") or candidate.get("formatted_address"),
                    "phone": source.get("international_phone_number") or candidate.get("international_phone_number") or phone,
                    "website": source.get("website") or candidate.get("website"),
                    "google_place_id": place_id or source.get("place_id"),
                }

                if isinstance(location, dict) and location.get("lat") is not None and location.get("lng") is not None:
                    normalized["google_location"] = {
                        "lat": location.get("lat"),
                        "lng": location.get("lng"),
                    }

                return {key: value for key, value in normalized.items() if value not in (None, "", [], {})}
        except Exception:
            return {}

    async def scrape(
        self,
        request: Any,
        org_context: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        api_key = self._get_api_key(org_context)
        if not api_key:
            logger.info("google_maps_scrape_mock_mode reason=no_api_key")
            return "success", self._build_mock_leads(request), ""

        query = self._build_text_search_query(request)
        if not query:
            logger.info("google_maps_scrape_empty_query")
            return "success", [], ""

        try:
            max_results = max(1, min(int(getattr(request, "max_results", 20) or 20), 50))
        except Exception:
            max_results = 20

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                places = await self._text_search_places(client, api_key, query, max_results)
                if not places:
                    logger.info("google_maps_scrape_no_places query=%s", query)
                    return "success", [], ""

                leads: List[Dict[str, Any]] = []
                seen_place_ids = set()
                for place in places:
                    if not isinstance(place, dict):
                        continue
                    place_id = str(place.get("place_id") or "").strip()
                    if place_id and place_id in seen_place_ids:
                        continue
                    details = await self._fetch_place_details(client, api_key, place_id) if place_id else {}
                    raw_lead = self._build_raw_lead(place, details)
                    if raw_lead:
                        dedupe_place_id = str(
                            ((raw_lead.get("metadata") or {}).get("place_id")) or place_id
                        ).strip()
                        if dedupe_place_id and dedupe_place_id in seen_place_ids:
                            continue
                        if dedupe_place_id:
                            seen_place_ids.add(dedupe_place_id)
                        leads.append(raw_lead)

                return "success", leads[:max_results], ""
        except Exception as exc:
            logger.exception("google_maps_scrape_failed error=%s", str(exc))
            return "success", [], ""
