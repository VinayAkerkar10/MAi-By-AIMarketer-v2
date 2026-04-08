from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Sequence


@dataclass
class EmailSendResult:
    recipient: str
    success: bool
    provider: str
    provider_message_id: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BulkEmailResult:
    provider: str
    recipient_count: int
    sent_count: int = 0
    failed_count: int = 0
    errors: List[dict] = field(default_factory=list)


class EmailProvider(ABC):
    provider_name: str = "abstract"

    @abstractmethod
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> EmailSendResult:
        raise NotImplementedError

    @abstractmethod
    async def send_bulk_email(
        self,
        recipients: Sequence[str],
        subject: str,
        html_body: str,
        text_body: str,
    ) -> BulkEmailResult:
        raise NotImplementedError
