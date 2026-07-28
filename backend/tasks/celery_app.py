# backend/tasks/celery_app.py
# Phase 2: Celery async task queue using Redis as broker
# Handles long-running AI orchestration jobs in background
# Gracefully degrades if Redis/Celery is not available

import logging

logger = logging.getLogger("AI-Digital-Company")

try:
    from celery import Celery
    from backend.core.config import CELERY_BROKER_URL, CELERY_RESULT_URL

    celery_app = Celery(
        "ai_digital_team",
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_URL,
        include=["backend.tasks.orchestration_task"]
    )

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_soft_time_limit=600,
        task_time_limit=720,
        result_expires=3600,
    )
    CELERY_AVAILABLE = True
    logger.info("Celery configured successfully.")

except Exception as e:
    logger.warning(f"Celery not available ({e}). Background jobs will be disabled.")
    celery_app = None
    CELERY_AVAILABLE = False
