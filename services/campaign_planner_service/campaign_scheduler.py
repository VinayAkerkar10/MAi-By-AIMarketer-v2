from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import logging

from sqlalchemy.orm import Session

from services.campaign_planner_service.tasks import execute_campaign_task
from services.shared.database import Campaign

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_to_utc(value: Optional[datetime], field_name: str) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        normalized = value.replace(tzinfo=timezone.utc)
    else:
        normalized = value.astimezone(timezone.utc)
    logger.info(
        {
            "field": field_name,
            "schedule_date": str(normalized),
            "schedule_date_tzinfo": str(normalized.tzinfo),
            "current_time": str(utc_now()),
            "current_time_tzinfo": str(utc_now().tzinfo),
        }
    )
    return normalized


def resolve_scheduled_at(campaign: Campaign) -> Optional[datetime]:
    return normalize_to_utc(getattr(campaign, "scheduled_at", None) or campaign.schedule_date, "scheduled_at")


def enqueue_campaign_execution(
    *,
    campaign_id: str,
    organization_id: str,
    auth_header: Optional[str],
    scheduled_at: Optional[datetime],
) -> str:
    scheduled_at = normalize_to_utc(scheduled_at, "scheduled_at")
    current_time = utc_now()
    logger.info(
        {
            "schedule_date": str(scheduled_at),
            "schedule_date_tzinfo": str(scheduled_at.tzinfo) if scheduled_at else None,
            "current_time": str(current_time),
            "current_time_tzinfo": str(current_time.tzinfo),
        }
    )
    if scheduled_at and scheduled_at > current_time:
        async_result = execute_campaign_task.apply_async(
            kwargs={
                "campaign_id": campaign_id,
                "organization_id": organization_id,
                "auth_header": auth_header,
            },
            eta=scheduled_at,
        )
    else:
        async_result = execute_campaign_task.delay(
            campaign_id=campaign_id,
            organization_id=organization_id,
            auth_header=auth_header,
        )

    return async_result.id


def fetch_due_campaigns(db: Session, *, limit: int = 100) -> List[Campaign]:
    now = utc_now()
    logger.info(
        {
            "schedule_date": None,
            "schedule_date_tzinfo": None,
            "current_time": str(now),
            "current_time_tzinfo": str(now.tzinfo),
        }
    )
    return (
        db.query(Campaign)
        .filter(
            Campaign.status == "scheduled",
            Campaign.scheduled_at.isnot(None),
            Campaign.scheduled_at <= now,
        )
        .order_by(Campaign.scheduled_at.asc())
        .limit(limit)
        .all()
    )
