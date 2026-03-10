from typing import Optional

from .lead_source_provider import LeadSourceProvider
from .github_provider import GitHubProvider
from .google_maps_provider import GoogleMapsProvider
from .linkedin_provider import LinkedInProvider
from .volza_provider import VolzaProvider


def get_provider(source_name: str) -> Optional[LeadSourceProvider]:
    providers = {
        "github": GitHubProvider,
        "google_maps": GoogleMapsProvider,
        "linkedin": LinkedInProvider,
        "volza": VolzaProvider,
    }

    provider_class = providers.get(str(source_name or "").strip().lower())
    if not provider_class:
        return None
    return provider_class()
