"""
scheduler.py — Background reminder engine using APScheduler.

Architecture decision: We use APScheduler's AsyncIOScheduler because it
integrates natively with asyncio and FastAPI's event loop. The scheduler runs
in the same process as FastAPI, which is acceptable for personal-scale usage.
For production at scale, extract this into a separate worker process or use
Celery Beat.

The job checks for upcoming events every REMINDER_CHECK_INTERVAL_SECONDS
(default: 60s). It prints reminders to stdout — replace the `print` call with
an actual WhatsApp API call, push notification, or email in production.
"""

import logging
from datetime import date, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from memocore.config import get_settings
from memocore.database import AsyncSessionLocal
from memocore.services.event_service import get_events_due_soon, mark_reminder_sent
from memocore.services.recurring_event_service import get_active_recurring_events

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level scheduler instance — started/stopped by FastAPI's lifespan
scheduler = AsyncIOScheduler()


async def _check_upcoming_events() -> None:
    """
    Periodic job: find events due within the next REMINDER_LEAD_TIME_MINUTES
    minutes and fire a reminder.

    Architecture note: We open a fresh session per job run. Using the same
    session across multiple scheduler ticks would cause issues with stale
    state and connection pool exhaustion.
    """
    now = datetime.now()
    lead = timedelta(minutes=settings.REMINDER_LEAD_TIME_MINUTES)
    target = now + lead

    logger.debug("Scheduler tick: checking events due around %s", target)

    async with AsyncSessionLocal() as db:
        try:
            events = await get_events_due_soon(db, target_date=target.date())

            for event in events:
                if event.time is None:
                    # All-day event: remind at the start of the day
                    _fire_reminder(event.title, event.date, None)
                    await mark_reminder_sent(db, event.id)
                    continue

                # Only remind when the event is within the lead-time window
                event_dt = datetime.combine(event.date, event.time)
                if now <= event_dt <= target:
                    minutes_away = int((event_dt - now).total_seconds() / 60)
                    _fire_reminder(event.title, event.date, event.time, minutes_away)
                    await mark_reminder_sent(db, event.id)

            # Also log active recurring events for visibility
            recurring = await get_active_recurring_events(db)
            if recurring:
                logger.debug(
                    "Active recurring events: %s",
                    [r.title for r in recurring],
                )

            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Error in _check_upcoming_events job")


def _fire_reminder(
    title: str,
    event_date: date,
    event_time,
    minutes_away: int | None = None,
) -> None:
    """
    Simulate sending a reminder message.

    In production, replace this with:
      - WhatsApp Cloud API send_message call
      - Push notification (FCM / APNs)
      - SMS (Twilio)
      - Email (SendGrid / SES)
    """
    time_str = str(event_time) if event_time else "all-day"
    eta = f" (~{minutes_away} min)" if minutes_away is not None else ""
    reminder_msg = (
        f"⏰ REMINDER: [{title}] on {event_date} at {time_str}{eta}"
    )
    # Logging at WARNING so it's visible without enabling DEBUG
    logger.warning(reminder_msg)
    print(reminder_msg)  # noqa: T201 — intentional stdout output for simulation


def start_scheduler() -> None:
    """Register jobs and start the scheduler. Called from FastAPI lifespan."""
    scheduler.add_job(
        _check_upcoming_events,
        trigger=IntervalTrigger(seconds=settings.REMINDER_CHECK_INTERVAL_SECONDS),
        id="check_upcoming_events",
        name="Check upcoming events and fire reminders",
        replace_existing=True,
        misfire_grace_time=30,  # if the job is late by < 30s, still run it
    )
    scheduler.start()
    logger.info(
        "Scheduler started — checking for reminders every %ds",
        settings.REMINDER_CHECK_INTERVAL_SECONDS,
    )


def stop_scheduler() -> None:
    """Gracefully shut down the scheduler. Called from FastAPI lifespan."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
