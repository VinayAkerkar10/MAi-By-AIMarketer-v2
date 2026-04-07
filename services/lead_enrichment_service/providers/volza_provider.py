from typing import Any, Dict, List, Tuple

from .lead_source_provider import LeadSourceProvider
from services.shared.api_keys import get_org_api_key


class VolzaProvider(LeadSourceProvider):
    def provider_name(self) -> str:
        return "volza"

    def validate_config(self, org_context: Dict[str, Any]) -> bool:
        if org_context.get("request") is not None:
            return True
        db = org_context.get("db_session")
        organization_id = org_context.get("organization_id")
        if db is None or not organization_id:
            return False
        api_key, _ = get_org_api_key(db, organization_id, self.provider_name())
        return bool(api_key)

    async def scrape(
        self,
        request: Any,
        org_context: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        return "unavailable", [], "Volza integration is not available. API access required."
