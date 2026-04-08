import logging
import os
from typing import Sequence

from services.campaign_planner_service.email_providers.base import BulkEmailResult
from services.campaign_planner_service.email_providers.smtp_provider import SMTPEmailProvider


logger = logging.getLogger(__name__)


class GmailProvider(SMTPEmailProvider):
    provider_name = "gmail"
    smtp_host = "smtp.gmail.com"
    smtp_port = 587
    use_tls = True
    require_auth = True

    def __init__(self) -> None:
        username = os.getenv("GMAIL_SMTP_USER") or os.getenv("EMAIL_USER") or ""
        password = os.getenv("GMAIL_SMTP_PASSWORD") or os.getenv("EMAIL_PASSWORD") or ""
        super().__init__(
            host=os.getenv("GMAIL_SMTP_HOST", self.smtp_host),
            port=int(os.getenv("GMAIL_SMTP_PORT", str(self.smtp_port))),
            username=username,
            password=password,
            from_email=os.getenv("EMAIL_FROM") or username,
            from_name=os.getenv("EMAIL_FROM_NAME") or "MAi Demo",
        )

    async def send_bulk_email(
        self,
        recipients: Sequence[str],
        subject: str,
        html_body: str,
        text_body: str,
    ) -> BulkEmailResult:
        if len(recipients) > 50:
            logger.warning(
                "gmail_bulk_send_limit_warning provider=%s recipient_count=%s limit=50",
                self.provider_name,
                len(recipients),
            )
        return await super().send_bulk_email(recipients, subject, html_body, text_body)
