import asyncio
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional, Sequence

from services.campaign_planner_service.email_providers.base import BulkEmailResult, EmailProvider, EmailSendResult


logger = logging.getLogger(__name__)


class SMTPEmailProvider(EmailProvider):
    smtp_host: str = ""
    smtp_port: int = 587
    use_tls: bool = True
    require_auth: bool = True

    def __init__(
        self,
        *,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None,
        timeout_seconds: int = 20,
    ) -> None:
        self.host = (host or self.smtp_host).strip()
        self.port = int(port or self.smtp_port)
        self.username = (username or "").strip()
        self.password = (password or "").strip()
        self.from_email = (from_email or os.getenv("EMAIL_FROM") or self.username).strip()
        self.from_name = (from_name or os.getenv("EMAIL_FROM_NAME") or "MAi by AIMarketer").strip()
        self.timeout_seconds = timeout_seconds

    def _build_message(self, to_email: str, subject: str, html_body: str, text_body: str) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{self.from_name} <{self.from_email}>" if self.from_name else self.from_email
        message["To"] = to_email
        message.attach(MIMEText(text_body or "", "plain", "utf-8"))
        message.attach(MIMEText(html_body or "", "html", "utf-8"))
        return message

    def _validate_configuration(self) -> Optional[str]:
        if not self.host:
            return "smtp_host_missing"
        if not self.port:
            return "smtp_port_missing"
        if not self.from_email:
            return "email_from_missing"
        if self.require_auth and (not self.username or not self.password):
            return "smtp_credentials_missing"
        return None

    def _send_via_smtp(self, to_email: str, subject: str, html_body: str, text_body: str) -> EmailSendResult:
        config_error = self._validate_configuration()
        if config_error:
            return EmailSendResult(
                recipient=to_email,
                success=False,
                provider=self.provider_name,
                error=config_error,
            )

        message = self._build_message(to_email, subject, html_body, text_body)
        try:
            with smtplib.SMTP(self.host, self.port, timeout=self.timeout_seconds) as smtp:
                smtp.ehlo()
                if self.use_tls:
                    smtp.starttls()
                    smtp.ehlo()
                if self.require_auth:
                    smtp.login(self.username, self.password)
                smtp.sendmail(self.from_email, [to_email], message.as_string())
            return EmailSendResult(
                recipient=to_email,
                success=True,
                provider=self.provider_name,
            )
        except Exception as exc:
            logger.warning(
                "email_send_failed provider=%s recipient=%s error=%s",
                self.provider_name,
                to_email,
                exc,
            )
            return EmailSendResult(
                recipient=to_email,
                success=False,
                provider=self.provider_name,
                error=str(exc),
            )

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> EmailSendResult:
        return await asyncio.to_thread(self._send_via_smtp, to_email, subject, html_body, text_body)

    async def send_bulk_email(
        self,
        recipients: Sequence[str],
        subject: str,
        html_body: str,
        text_body: str,
    ) -> BulkEmailResult:
        result = BulkEmailResult(provider=self.provider_name, recipient_count=len(recipients))
        for recipient in recipients:
            send_result = await self.send_email(recipient, subject, html_body, text_body)
            if send_result.success:
                result.sent_count += 1
            else:
                result.failed_count += 1
                result.errors.append(
                    {
                        "recipient": recipient,
                        "error": send_result.error or "send_failed",
                    }
                )
        return result
