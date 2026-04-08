import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from services.shared.celery_app import celery_app
from services.shared.database import Campaign, SessionLocal


logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@celery_app.task(name="campaigns.execute_campaign_task")
def execute_campaign_task(
    *,
    campaign_id: str,
    organization_id: str,
    auth_header: Optional[str] = None,
) -> None:
    from services.campaign_planner_service.main import execute_campaign

    db = SessionLocal()
    try:
        asyncio.run(
            execute_campaign(
                campaign_id=campaign_id,
                db=db,
                organization_id=organization_id,
                auth_header=auth_header,
            )
        )
    except Exception as exc:
        db.rollback()
        campaign = (
            db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.organization_id == organization_id,
            )
            .first()
        )
        if campaign:
            campaign.status = "failed"
            campaign.last_error = str(exc)
            campaign.updated_at = utc_now()
            db.commit()
        logger.exception("campaign_task_failed campaign_id=%s organization_id=%s", campaign_id, organization_id)
        raise
    finally:
        db.close()
