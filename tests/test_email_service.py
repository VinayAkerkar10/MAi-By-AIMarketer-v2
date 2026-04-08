import pytest

from services.campaign_planner_service.email_providers.base import BulkEmailResult, EmailSendResult, EmailProvider
from services.campaign_planner_service.email_service import EmailService


class DummyProvider(EmailProvider):
    provider_name = "dummy"

    async def send_email(self, to_email, subject, html_body, text_body):
        return EmailSendResult(
            recipient=to_email,
            success=True,
            provider=self.provider_name,
        )

    async def send_bulk_email(self, recipients, subject, html_body, text_body):
        return BulkEmailResult(
            provider=self.provider_name,
            recipient_count=len(recipients),
            sent_count=len(recipients),
            failed_count=0,
        )


@pytest.mark.asyncio
async def test_campaign_send_filters_invalid_and_duplicate_recipients(monkeypatch):
    monkeypatch.setenv("EMAIL_VALIDATE_MX", "false")
    service = EmailService(provider=DummyProvider())

    result = await service.send_campaign(
        recipients=[
            {"email": "valid@example.com", "name": "Alice"},
            {"email": "valid@example.com", "name": "Alice Duplicate"},
            {"email": "not-an-email", "name": "Broken"},
            {"email": None, "name": "Missing"},
        ],
        subject_template="Hello {{name}}",
        body_template="<p>Hi {{name}} from {{company}}</p>",
        cta_label="Open",
        cta_url="https://example.com",
    )

    assert result.provider == "dummy"
    assert result.requested == 4
    assert result.accepted == 1
    assert result.rejected == 3
    assert result.sent == 1
    assert result.failed == 0
