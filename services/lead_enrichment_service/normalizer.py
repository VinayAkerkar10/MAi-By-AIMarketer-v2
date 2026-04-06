from typing import Any, Dict

from services.lead_enrichment_service.schema import LeadSchema, NOT_AVAILABLE, normalize_empty


CANONICAL_FIELDS = {
    "name",
    "email",
    "phone",
    "company",
    "designation",
    "location",
    "source",
    "website",
    "linkedin",
    "github",
    "description",
    "industry",
    "source_metadata",
}

SOURCE_METADATA_EXCLUDE = {
    "business_name",
    "company_name",
    "name",
    "contact_name",
    "address",
    "location",
    "html_url",
    "blog",
    "url",
    "website",
    "linkedin_url",
    "bio",
    "description",
    "category",
    "type",
    "industry",
    "source",
    "email",
    "phone",
    "designation",
    "job_title",
    "metadata",
}


def _first_value(raw: Dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = normalize_empty(raw.get(key))
        if value is not None:
            return value
    return None


def _collect_source_metadata(raw: Dict[str, Any]) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {}

    existing = raw.get("source_metadata")
    if isinstance(existing, dict):
        metadata.update(existing)

    raw_metadata = raw.get("metadata")
    if isinstance(raw_metadata, dict):
        metadata.update(raw_metadata)

    for key, value in raw.items():
        if key in CANONICAL_FIELDS or key in SOURCE_METADATA_EXCLUDE:
            continue
        cleaned = normalize_empty(value)
        if cleaned is not None:
            metadata[key] = cleaned

    raw_payload = raw.get("raw_payload")
    if isinstance(raw_payload, dict) and "raw_payload" not in metadata:
        metadata["raw_payload"] = raw_payload

    return metadata


def _with_not_available(value: Any) -> Any:
    normalized = normalize_empty(value)
    if normalized is None:
        return NOT_AVAILABLE
    return normalized


def _build_legacy_aliases(payload: Dict[str, Any], raw_data: Dict[str, Any]) -> Dict[str, Any]:
    source_metadata = payload.get("source_metadata", {})
    raw_payload = raw_data.get("raw_payload")

    aliases = {
        "company_name": payload["company"],
        "business_name": payload["company"],
        "contact_name": payload["name"],
        "address": payload["location"],
        "linkedin_url": payload["linkedin"],
        "github_url": payload["github"],
        "category": payload["industry"],
        "metadata": source_metadata if isinstance(source_metadata, dict) else {},
    }

    if isinstance(raw_payload, dict):
        aliases["raw_payload"] = raw_payload

    scraped_at = normalize_empty(raw_data.get("scraped_at"))
    if scraped_at is not None:
        aliases["scraped_at"] = scraped_at

    return aliases


def normalize_lead(source: str, raw: dict) -> dict:
    raw_data = raw if isinstance(raw, dict) else {}

    normalized_source = normalize_empty(source) or _first_value(raw_data, "source") or NOT_AVAILABLE
    website = _first_value(raw_data, "website", "blog", "url", "html_url")
    github = _first_value(raw_data, "github", "html_url") if normalized_source == "github" else _first_value(raw_data, "github")
    linkedin = _first_value(raw_data, "linkedin", "linkedin_url")

    payload = {
        "name": _first_value(raw_data, "name", "contact_name") or NOT_AVAILABLE,
        "email": _first_value(raw_data, "email") or NOT_AVAILABLE,
        "phone": _first_value(raw_data, "phone") or NOT_AVAILABLE,
        "company": _first_value(raw_data, "company", "business_name", "company_name") or NOT_AVAILABLE,
        "designation": _first_value(raw_data, "designation", "job_title") or NOT_AVAILABLE,
        "location": _first_value(raw_data, "location", "address") or NOT_AVAILABLE,
        "source": normalized_source,
        "website": website or NOT_AVAILABLE,
        "linkedin": linkedin or NOT_AVAILABLE,
        "github": github or NOT_AVAILABLE,
        "description": _first_value(raw_data, "description", "bio") or NOT_AVAILABLE,
        "industry": _first_value(raw_data, "industry", "category", "type") or NOT_AVAILABLE,
        "source_metadata": _collect_source_metadata(raw_data),
    }

    normalized_payload = LeadSchema(**payload).model_dump()

    for key, value in list(normalized_payload.items()):
        if key == "source_metadata":
            continue
        normalized_payload[key] = _with_not_available(value)

    normalized_payload.update(_build_legacy_aliases(normalized_payload, raw_data))
    return normalized_payload
