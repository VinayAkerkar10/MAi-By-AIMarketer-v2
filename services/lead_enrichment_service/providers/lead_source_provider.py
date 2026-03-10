from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple


class LeadSourceProvider(ABC):
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError()

    def validate_config(self, org_context: Dict[str, Any]) -> bool:
        """
        Validate provider configuration before scraping.
        org_context will later include organization-level configuration.
        """
        return True

    @abstractmethod
    async def scrape(
        self,
        request: Any,
        org_context: Dict[str, Any],
    ) -> Tuple[str, List[Dict[str, Any]], str]:
        raise NotImplementedError()
