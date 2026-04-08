import logging
import os
from typing import Optional, Sequence

import httpx

from services.campaign_planner_service.email_providers.base import BulkEmailResult, EmailSendResult
from services.campaign_planner_service.email_providers.smtp_provider import SMTPEmailProvider


logger = logging.getLogger(__name__)


class MailrelayProvider(SMTPEmailProvider):
    provider_name = "mailrelay"
    smtp_host = "smtp.mailrelay.com"
    smtp_port = 587
    use_tls = True
    require_auth = True

    def __init__(self) -> None:
        super().__init__(
            host=os.getenv("MAILRELAY_SMTP_HOST", self.smtp_host),
            port=int(os.getenv("MAILRELAY_SMTP_PORT", str(self.smtp_port))),
            username=os.getenv("MAILRELAY_SMTP_USER") or "",
            password=os.getenv("MAILRELAY_SMTP_PASSWORD") or "",
            from_email=os.getenv("EMAIL_FROM") or os.getenv("MAILRELAY_FROM_EMAIL") or "",
            from_name=os.getenv("EMAIL_FROM_NAME") or os.getenv("MAILRELAY_FROM_NAME") or "MAi by AIMarketer",
        )
        self.api_base_url = (os.getenv("MAILRELAY_API_BASE_URL") or "").strip().rstrip("/")
        self.api_token = (os.getenv("MAILRELAY_API_TOKEN") or "").strip()
        self.api_enabled = str(os.getenv("MAILRELAY_USE_API", "false")).strip().lower() == "true"

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> EmailSendResult:
        if self.api_enabled:
            api_result = await self._send_via_api(to_email, subject, html_body, text_body)
            if api_result.success or not api_result.error:
                return api_result
            logger.warning(
                "mailrelay_api_fallback_to_smtp recipient=%s error=%s",
                to_email,
                api_result.error,
            )
        return await super().send_email(to_email, subject, html_body, text_body)

    async def send_bulk_email(
        self,
        recipients: Sequence[str],
        subject: str,
        html_body: str,
        text_body: str,
    ) -> BulkEmailResult:
        return await super().send_bulk_email(recipients, subject, html_body, text_body)

    async def _send_via_api(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> EmailSendResult:
        if not (self.api_enabled and self.api_base_url and self.api_token and self.from_email):
            return EmailSendResult(
                recipient=to_email,
                success=False,
                provider=self.provider_name,
                error="mailrelay_api_not_configured",
            )

        payload = {
            "from": {"email": self.from_email, "name": self.from_name},
            "to": [{"email": to_email, "name": to_email}],
            "subject": subject,
            "html_part": html_body,
            "text_part": text_body,
        }
        headers = {"x-auth-token": self.api_token, "content-type": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=20) as client:
                response = await client.post(f"{self.api_base_url}/send_emails", headers=headers, json=payload)
            response.raise_for_status()
            body = response.json() if response.content else {}
            return EmailSendResult(
                recipient=to_email,
                success=True,
                provider=self.provider_name,
                provider_message_id=str(body.get("id") or body.get("message_id") or "").strip() or None,
            )
        except Exception as exc:
            return EmailSendResult(
                recipient=to_email,
                success=False,
                provider=self.provider_name,
                error=str(exc),
            )
