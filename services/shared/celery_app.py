# Celery App Configuration
# Created by Mrityunjay Pandey, AIMarketer Pvt. Ltd.

from celery import Celery
import os
import logging

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

logger.info(
    {
        "redis_url": REDIS_URL,
        "celery_broker": CELERY_BROKER_URL,
        "environment": os.getenv("ENV"),
    }
)

celery_app = Celery(
    "mai_tasks",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["services.campaign_planner_service.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
