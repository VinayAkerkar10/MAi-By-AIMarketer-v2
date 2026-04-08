import os

from services.campaign_planner_service.email_providers import GmailProvider, MailHogProvider, MailrelayProvider
from services.campaign_planner_service.email_providers.base import EmailProvider


def get_email_provider() -> EmailProvider:
    provider_name = str(os.getenv("EMAIL_PROVIDER") or "mailhog").strip().lower()

    if provider_name == "mailhog":
        return MailHogProvider()
    if provider_name == "gmail":
        return GmailProvider()
    if provider_name == "mailrelay":
        return MailrelayProvider()

    raise ValueError(
        f"Invalid EMAIL_PROVIDER '{provider_name}'. Expected one of: mailhog, gmail, mailrelay."
    )
