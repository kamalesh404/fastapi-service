"""
Celery service for async task processing.

Provides task definitions, routing, and monitoring.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from celery import Celery, Task
from celery.schedules import crontab
from celery.signals import task_prerun, task_postrun, task_failure

from app.core.config import settings
from app.monitoring.metrics import record_celery_task
from app.monitoring.logging import get_logger

logger = get_logger("app.celery")


# Create Celery app
celery_app = Celery(
    "fastapi_service",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.email",
        "app.tasks.notifications",
        "app.tasks.maintenance",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    result_extended=True,

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task execution
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes hard limit
    task_soft_time_limit=240,  # 4 minutes soft limit

    # Worker
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    worker_disable_rate_limits=False,

    # Result backend
    result_expires=3600,  # 1 hour
    result_compression="gzip",

    # Beat schedule
    beat_schedule={
        "cleanup-expired-tokens": {
            "task": "app.tasks.maintenance.cleanup_expired_tokens",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3 AM
        },
        "cleanup-expired-files": {
            "task": "app.tasks.maintenance.cleanup_expired_files",
            "schedule": crontab(hour=4, minute=0),
        },
        "send-daily-reports": {
            "task": "app.tasks.maintenance.send_daily_reports",
            "schedule": crontab(hour=8, minute=0),
        },
        "sync-search-index": {
            "task": "app.tasks.maintenance.sync_search_index",
            "schedule": crontab(minute="*/15"),  # Every 15 minutes
        },
    },
)


class BaseTask(Task):
    """Base task class with common functionality."""

    autoretry_for = (Exception,)
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True
    max_retries = 3

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails after all retries."""
        logger.error(
            "Task failed permanently",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            args=args,
            kwargs=kwargs,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried."""
        logger.warning(
            "Task retry",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            retry_count=self.request.retries,
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)


# Signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwargs):
    """Signal handler for task start."""
    logger.info(
        "Task started",
        task_id=task_id,
        task_name=sender.name if sender else None,
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwargs):
    """Signal handler for task completion."""
    if sender and hasattr(sender, "name"):
        duration = 0  # Would need timing context
        record_celery_task(sender.name, duration, state == "SUCCESS")
        logger.info(
            "Task completed",
            task_id=task_id,
            task_name=sender.name,
            state=state,
        )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Signal handler for task failure."""
    if sender:
        logger.error(
            "Task failed",
            task_id=task_id,
            task_name=sender.name,
            error=str(exception),
        )


# =============================================================================
# Task Definitions
# =============================================================================

@celery_app.task(bind=True, base=BaseTask, name="app.tasks.email.send_email")
def send_email_task(
    self,
    to: str,
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    from_email: Optional[str] = None,
) -> Dict[str, Any]:
    """Send email asynchronously."""
    # TODO: Implement email sending
    logger.info("Sending email", to=to, subject=subject)
    return {"status": "sent", "to": to}


@celery_app.task(bind=True, base=BaseTask, name="app.tasks.email.send_bulk_email")
def send_bulk_email_task(
    self,
    recipients: List[str],
    subject: str,
    body: str,
    html_body: Optional[str] = None,
    batch_size: int = 50,
) -> Dict[str, Any]:
    """Send bulk emails in batches."""
    # TODO: Implement bulk email sending
    logger.info("Sending bulk email", count=len(recipients))
    return {"status": "completed", "count": len(recipients)}


@celery_app.task(bind=True, base=BaseTask, name="app.tasks.notifications.send_push")
def send_push_notification_task(
    self,
    user_id: int,
    title: str,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send push notification."""
    # TODO: Implement push notification
    logger.info("Sending push notification", user_id=user_id)
    return {"status": "sent", "user_id": user_id}


@celery_app.task(bind=True, base=BaseTask, name="app.tasks.maintenance.cleanup_expired_tokens")
def cleanup_expired_tokens_task(self) -> Dict[str, Any]:
    """Clean up expired refresh tokens."""
    from app.db.session import db_manager
    from app.models.user import RefreshToken
    from sqlalchemy import delete
    from datetime import datetime, timezone

    async def cleanup():
        async with db_manager.session() as session:
            result = await session.execute(
                delete(RefreshToken).where(
                    RefreshToken.expires_at < datetime.now(timezone.utc)
                )
            )
            await session.commit()
            return result.rowcount

    # Run async cleanup
    import asyncio
    count = asyncio.run(cleanup())

    logger.info("Cleaned up expired tokens", count=count)
    return {"status": "completed", "deleted": count}


@celery_app.task(bind=True, base=BaseTask, name="app.tasks.maintenance.cleanup_expired_files")
def cleanup_expired_files_task(self) -> Dict[str, Any]:
    """Clean up expired uploaded files."""
    # TODO: Implement file cleanup
    logger.info("Cleaning up expired files")
    return {"status": "completed", "deleted": 0}


@celery_app.task(bind=True, base=BaseTask, name="app.tasks.maintenance.send_daily_reports")
def send_daily_reports_task(self) -> Dict[str, Any]:
    """Send daily analytics reports."""
    # TODO: Implement daily reports
    logger.info("Sending daily reports")
    return {"status": "completed"}


@celery_app.task(bind=True, base=BaseTask, name="app.tasks.maintenance.sync_search_index")
def sync_search_index_task(self) -> Dict[str, Any]:
    """Sync search index with database."""
    # TODO: Implement search index sync
    logger.info("Syncing search index")
    return {"status": "completed"}


# =============================================================================
# Utility Functions
# =============================================================================

def enqueue_task(task_name: str, *args, **kwargs) -> Any:
    """Enqueue a task by name."""
    return celery_app.send_task(task_name, args=args, kwargs=kwargs)


def schedule_task(task_name: str, *args, countdown: int = None, eta: datetime = None, **kwargs) -> Any:
    """Schedule a task for future execution."""
    return celery_app.send_task(
        task_name,
        args=args,
        kwargs=kwargs,
        countdown=countdown,
        eta=eta,
    )


def get_task_result(task_id: str) -> Any:
    """Get task result by ID."""
    return celery_app.AsyncResult(task_id)


def revoke_task(task_id: str, terminate: bool = False) -> bool:
    """Revoke a task."""
    celery_app.control.revoke(task_id, terminate=terminate)
    return True