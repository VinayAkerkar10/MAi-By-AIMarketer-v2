import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from services.campaign_planner_service.email_provider_factory import get_email_provider
from services.campaign_planner_service.email_providers.base import BulkEmailResult, EmailProvider, EmailSendResult
from services.campaign_planner_service.email_templates import build_campaign_email, render_tokens
from services.campaign_planner_service.email_validation import validate_recipients


logger = logging.getLogger(__name__)


@dataclass
class BulkCampaignResult:
    requested: int = 0
    accepted: int = 0
    rejected: int = 0
    sent: int = 0
    failed: int = 0
    provider: str = ""
    failures: List[Dict[str, Any]] = field(default_factory=list)


class EmailService:
    def __init__(self, provider: Optional[EmailProvider] = None) -> None:
        self.provider = provider or get_email_provider()
        self.retry_attempts = max(1, int(os.getenv("EMAIL_MAX_RETRIES", "3")))
        self.retry_base_delay_seconds = max(1, int(os.getenv("EMAIL_RETRY_BASE_DELAY_SECONDS", "2")))
        self.check_mx = str(os.getenv("EMAIL_VALIDATE_MX", "false")).strip().lower() == "true"
        self.company_name = os.getenv("EMAIL_COMPANY_NAME", "MAi by AIMarketer")

    async def send_email(
        self,
        *,
        to_email: str,
        subject: str,
        html_body: str,
        text_body: str,
    ) -> EmailSendResult:
        logger.info(
            "email_send_start provider=%s recipient_count=1",
            self.provider.provider_name,
        )
        try:
            result = await self.provider.send_email(to_email, subject, html_body, text_body)
            if result.success:
                logger.info(
                    "email_send_success provider=%s recipient=%s",
                    result.provider,
                    result.recipient,
                )
            else:
                logger.warning(
                    "email_send_failure provider=%s recipient=%s error=%s",
                    result.provider,
                    result.recipient,
                    result.error,
                )
            return result
        except Exception as exc:
            logger.exception(
                "email_send_unhandled provider=%s recipient=%s",
                self.provider.provider_name,
                to_email,
            )
            return EmailSendResult(
                recipient=to_email,
                success=False,
                provider=self.provider.provider_name,
                error=str(exc),
            )

    async def send_bulk_email(
        self,
        *,
        recipients: List[str],
        subject: str,
        html_body: str,
        text_body: str,
    ) -> BulkEmailResult:
        logger.info(
            "bulk_email_send_start provider=%s recipient_count=%s",
            self.provider.provider_name,
            len(recipients),
        )
        try:
            result = await self.provider.send_bulk_email(recipients, subject, html_body, text_body)
            log_method = logger.info if result.failed_count == 0 else logger.warning
            log_method(
                "bulk_email_send_complete provider=%s recipient_count=%s sent=%s failed=%s",
                result.provider,
                result.recipient_count,
                result.sent_count,
                result.failed_count,
            )
            return result
        except Exception as exc:
            logger.exception(
                "bulk_email_send_unhandled provider=%s recipient_count=%s",
                self.provider.provider_name,
                len(recipients),
            )
            return BulkEmailResult(
                provider=self.provider.provider_name,
                recipient_count=len(recipients),
                sent_count=0,
                failed_count=len(recipients),
                errors=[{"recipient": recipient, "error": str(exc)} for recipient in recipients],
            )

    async def send_campaign(
        self,
        *,
        recipients: List[Dict[str, Any]],
        subject_template: str,
        body_template: str,
        cta_label: str,
        cta_url: str,
    ) -> BulkCampaignResult:
        should_check_mx = self.check_mx or self.provider.provider_name == "mailrelay"
        validation_report = validate_recipients(recipients, check_mx=should_check_mx)
        result = BulkCampaignResult(
            requested=len(recipients),
            accepted=len(validation_report.accepted),
            rejected=len(validation_report.rejected),
            provider=self.provider.provider_name,
        )
        result.failures.extend(
            {
                "recipient": item.email,
                "error": item.reason,
            }
            for item in validation_report.rejected
        )

        if not validation_report.accepted:
            logger.warning(
                "campaign_send_no_valid_recipients provider=%s requested=%s rejected=%s",
                self.provider.provider_name,
                result.requested,
                result.rejected,
            )
            return result

        for recipient in validation_report.accepted:
            variables = {
                "name": recipient.name or "there",
                "company": recipient.company or "your team",
                "email": recipient.email,
            }
            subject = render_tokens(subject_template, variables)
            body_html = render_tokens(body_template, variables)
            rendered = build_campaign_email(
                subject=subject,
                headline=f"Hi {variables['name']},",
                body_html=body_html,
                cta_label=cta_label,
                cta_url=render_tokens(cta_url, variables),
                preheader=subject,
                company_name=self.company_name,
            )

            last_send_result: Optional[EmailSendResult] = None
            for attempt in range(1, self.retry_attempts + 1):
                last_send_result = await self.send_email(
                    to_email=recipient.email,
                    subject=rendered["subject"],
                    html_body=rendered["html"],
                    text_body=rendered["text"],
                )
                if last_send_result.success:
                    result.sent += 1
                    break
                if attempt < self.retry_attempts:
                    await asyncio.sleep(self.retry_base_delay_seconds * attempt)

            if last_send_result and not last_send_result.success:
                result.failed += 1
                result.failures.append(
                    {
                        "recipient": recipient.email,
                        "error": last_send_result.error or "send_failed",
                    }
                )

        logger.info(
            "campaign_send_complete provider=%s requested=%s accepted=%s rejected=%s sent=%s failed=%s",
            result.provider,
            result.requested,
            result.accepted,
            result.rejected,
            result.sent,
            result.failed,
        )
        return result
