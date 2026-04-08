import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from email_validator import EmailNotValidError, validate_email


EMAIL_REGEX = re.compile(r"^[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}$", re.IGNORECASE)
EMPTY_EMAIL_MARKERS = {"", "n/a", "na", "none", "null", "not available", "unknown"}


@dataclass
class ValidatedRecipient:
    email: str
    name: Optional[str] = None
    company: Optional[str] = None
    source: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RejectedRecipient:
    email: Optional[str]
    reason: str
    raw: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecipientValidationReport:
    accepted: List[ValidatedRecipient] = field(default_factory=list)
    rejected: List[RejectedRecipient] = field(default_factory=list)


def normalize_email(value: Any) -> Optional[str]:
    if value is None:
        return None
    email = str(value).strip()
    if not email:
        return None
    if email.lower() in EMPTY_EMAIL_MARKERS:
        return None
    return email


def validate_recipient(
    recipient: Dict[str, Any],
    *,
    check_mx: bool = False,
) -> Optional[ValidatedRecipient]:
    raw_email = normalize_email(recipient.get("email"))
    if not raw_email:
        return None

    if not EMAIL_REGEX.match(raw_email):
        return None

    try:
        normalized = validate_email(raw_email, check_deliverability=check_mx).normalized
    except EmailNotValidError:
        return None

    return ValidatedRecipient(
        email=normalized,
        name=str(recipient.get("name") or recipient.get("contact_name") or "").strip() or None,
        company=str(
            recipient.get("company")
            or recipient.get("business_name")
            or recipient.get("company_name")
            or ""
        ).strip() or None,
        source=str(recipient.get("source") or "").strip() or None,
        raw=recipient if isinstance(recipient, dict) else {},
    )


def validate_recipients(
    recipients: List[Dict[str, Any]],
    *,
    check_mx: bool = False,
) -> RecipientValidationReport:
    report = RecipientValidationReport()
    seen = set()

    for recipient in recipients:
        raw = recipient if isinstance(recipient, dict) else {}
        raw_email = normalize_email(raw.get("email"))
        if not raw_email:
            report.rejected.append(
                RejectedRecipient(email=None, reason="missing_email", raw=raw),
            )
            continue

        validated = validate_recipient(raw, check_mx=check_mx)
        if not validated:
            report.rejected.append(
                RejectedRecipient(email=raw_email, reason="invalid_email", raw=raw),
            )
            continue

        dedupe_key = validated.email.lower()
        if dedupe_key in seen:
            report.rejected.append(
                RejectedRecipient(email=validated.email, reason="duplicate_email", raw=raw),
            )
            continue

        seen.add(dedupe_key)
        report.accepted.append(validated)

    return report
