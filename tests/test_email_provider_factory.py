import os

import pytest

from services.campaign_planner_service.email_provider_factory import get_email_provider
from services.campaign_planner_service.email_providers.gmail_provider import GmailProvider
from services.campaign_planner_service.email_providers.mailhog_provider import MailHogProvider
from services.campaign_planner_service.email_providers.mailrelay_provider import MailrelayProvider


def test_factory_returns_mailhog(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "mailhog")
    provider = get_email_provider()
    assert isinstance(provider, MailHogProvider)


def test_factory_returns_gmail(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "gmail")
    provider = get_email_provider()
    assert isinstance(provider, GmailProvider)


def test_factory_returns_mailrelay(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "mailrelay")
    provider = get_email_provider()
    assert isinstance(provider, MailrelayProvider)


def test_factory_rejects_invalid_provider(monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "invalid-provider")
    with pytest.raises(ValueError):
        get_email_provider()
