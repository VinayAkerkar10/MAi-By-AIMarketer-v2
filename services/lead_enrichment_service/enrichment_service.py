from copy import deepcopy
from typing import Any, Dict, List

from services.lead_enrichment_service.providers.provider_registry import get_provider


ENRICHMENT_PROVIDERS = ["linkedin", "google_maps", "github", "email"]


def _is_non_empty(value: Any) -> bool:
    return value not in (None, "", [], {})


def _merge_customer_data(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    merged = deepcopy(base)

    for key, value in (patch or {}).items():
        if not _is_non_empty(value):
            continue
        if _is_non_empty(merged.get(key)):
            continue
        merged[key] = value

    return merged


async def enrich_customer(customer: dict, org_context: dict) -> dict:
    """
    Enrich a single uploaded customer record using multiple providers.

    The original customer payload is preserved and only missing, non-empty
    fields are added from provider results.
    """
    base_customer: Dict[str, Any] = deepcopy(customer or {})
    enriched_customer: Dict[str, Any] = deepcopy(base_customer)
    provider_results: List[Dict[str, Any]] = []

    for provider_name in ENRICHMENT_PROVIDERS:
        provider = get_provider(provider_name)
        if not provider:
            provider_results.append({
                "provider": provider_name,
                "success": False,
                "error": "Provider not found.",
                "data": {},
            })
            continue

        try:
            is_configured = provider.validate_config(org_context)
        except Exception as exc:
            provider_results.append({
                "provider": provider_name,
                "success": False,
                "error": f"Provider config validation failed: {str(exc)}",
                "data": {},
            })
            continue

        if not is_configured:
            provider_results.append({
                "provider": provider_name,
                "success": False,
                "error": "Provider not configured for this organization.",
                "data": {},
            })
            continue

        enrich_method = getattr(provider, "enrich", None)
        if not callable(enrich_method):
            provider_results.append({
                "provider": provider_name,
                "success": False,
                "error": "Provider does not implement enrich().",
                "data": {},
            })
            continue

        try:
            provider_data = await enrich_method(base_customer, org_context)
            if not isinstance(provider_data, dict):
                provider_results.append({
                    "provider": provider_name,
                    "success": False,
                    "error": "Provider enrich() returned a non-dict response.",
                    "data": {},
                })
                continue

            provider_results.append({
                "provider": provider_name,
                "success": True,
                "data": provider_data,
            })
            enriched_customer = _merge_customer_data(enriched_customer, provider_data)
        except Exception as exc:
            provider_results.append({
                "provider": provider_name,
                "success": False,
                "error": str(exc),
                "data": {},
            })

    enriched_customer["enrichment_meta"] = {
        "providers": provider_results,
    }
    return enriched_customer
