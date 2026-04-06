from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


NOT_AVAILABLE = "Not Available"


def normalize_empty(value: Any) -> Optional[Any]:
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned:
            return None
        if cleaned.lower() in {"n/a", "na"}:
            return None
        return cleaned
    return value


class LeadSchema(BaseModel):
    name: str = NOT_AVAILABLE
    email: str = NOT_AVAILABLE
    phone: str = NOT_AVAILABLE
    company: str = NOT_AVAILABLE
    designation: str = NOT_AVAILABLE
    location: str = NOT_AVAILABLE
    source: str = NOT_AVAILABLE
    website: str = NOT_AVAILABLE
    linkedin: str = NOT_AVAILABLE
    github: str = NOT_AVAILABLE
    description: str = NOT_AVAILABLE
    industry: str = NOT_AVAILABLE
    source_metadata: Dict[str, Any] = Field(default_factory=dict)
