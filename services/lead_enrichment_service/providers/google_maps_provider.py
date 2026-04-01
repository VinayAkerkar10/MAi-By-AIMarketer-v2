import os
from typing import Any, Dict, List, Optional, Tuple

import httpx

from .lead_source_provider import LeadSourceProvider
from services.shared.api_keys import get_org_api_key


class GoogleMapsProvider(LeadSourceProvider):
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
        return bool(self._get_api_key(org_context))

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
        return "error", [], "Google Maps source is not configured."
