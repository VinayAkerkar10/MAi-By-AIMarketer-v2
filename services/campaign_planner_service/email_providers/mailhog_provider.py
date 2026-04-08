import logging
import os
from typing import Sequence

from services.campaign_planner_service.email_providers.base import BulkEmailResult
from services.campaign_planner_service.email_providers.smtp_provider import SMTPEmailProvider


logger = logging.getLogger(__name__)


class MailHogProvider(SMTPEmailProvider):
    provider_name = "mailhog"
    smtp_host = "mailhog"
    smtp_port = 1025
    use_tls = False
    require_auth = False

    def __init__(self) -> None:
        super().__init__(
            host=os.getenv("MAILHOG_SMTP_HOST", self.smtp_host),
            port=int(os.getenv("MAILHOG_SMTP_PORT", str(self.smtp_port))),
            from_email=os.getenv("EMAIL_FROM") or "noreply@local.test",
            from_name=os.getenv("EMAIL_FROM_NAME") or "MAi Local",
        )

    async def send_bulk_email(
        self,
        recipients: Sequence[str],
        subject: str,
        html_body: str,
        text_body: str,
    ) -> BulkEmailResult:
        logger.info(
            "mailhog_bulk_send provider=%s recipient_count=%s safety=local_only",
            self.provider_name,
            len(recipients),
        )
        return await super().send_bulk_email(recipients, subject, html_body, text_body)
