import base64
import hashlib
import os
from typing import Optional, Tuple

from cryptography.fernet import Fernet
from sqlalchemy.orm import Session

from .database import OrganizationApiKey


def _build_fernet() -> Fernet:
    configured_key = (os.getenv("API_KEY_ENCRYPTION_KEY") or "").strip()
    if configured_key:
        return Fernet(configured_key.encode("utf-8"))

    jwt_secret = (os.getenv("JWT_SECRET_KEY") or "").strip()
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET_KEY is required to derive API key encryption key.")

    digest = hashlib.sha256(jwt_secret.encode("utf-8")).digest()
    derived_key = base64.urlsafe_b64encode(digest)
    return Fernet(derived_key)


def encrypt_api_key(plain_api_key: str) -> str:
    fernet = _build_fernet()
    token = fernet.encrypt(str(plain_api_key).encode("utf-8"))
    return token.decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str:
    fernet = _build_fernet()
    value = fernet.decrypt(str(encrypted_api_key).encode("utf-8"))
    return value.decode("utf-8")


def mask_api_key(value: Optional[str]) -> str:
    text = str(value or "")
    if len(text) <= 8:
        return "*" * len(text)
    return f"{text[:4]}{'*' * (len(text) - 8)}{text[-4:]}"


def get_org_api_key_record(
    db: Session,
    organization_id: str,
    provider_name: str,
) -> Optional[OrganizationApiKey]:
    return (
        db.query(OrganizationApiKey)
        .filter(
            OrganizationApiKey.organization_id == organization_id,
            OrganizationApiKey.provider_name == str(provider_name or "").strip().lower(),
            OrganizationApiKey.status == "active",
        )
        .first()
    )


def get_org_api_key(
    db: Session,
    organization_id: str,
    provider_name: str,
) -> Tuple[Optional[str], Optional[str]]:
    row = get_org_api_key_record(
        db=db,
        organization_id=organization_id,
        provider_name=provider_name,
    )
    if not row:
        return None, None
    return decrypt_api_key(row.api_key), row.id
