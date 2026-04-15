"""
Background scheduler — runs as an asyncio task inside the FastAPI lifespan.

Every 60 seconds it checks all alerts. For each due alert it:
1. Scrapes jobs with the alert's search params
2. Filters by min_salary
3. Finds links not in seen_links (= new jobs)
4. Sends a notification if there are new jobs
5. Updates seen_links and last_run
"""

import asyncio
import logging
from datetime import UTC, datetime

import aiohttp

from .alerts import MAX_SEEN_LINKS, load_alerts, save_alerts
from .models import JobListing, JobSearchRequest

logger = logging.getLogger(__name__)

# How often the scheduler wakes up to check alerts (seconds)
POLL_INTERVAL = 60


async def run_scheduler() -> None:
    """Main scheduler loop. Runs forever until cancelled."""
    logger.info("Scheduler started (poll interval: %ds)", POLL_INTERVAL)
    while True:
        await asyncio.sleep(POLL_INTERVAL)
        try:
            await _check_alerts()
        except Exception as e:
            logger.error("Scheduler cycle error: %s", e)


# ──────────────────────────────────────────
# Internal helpers
# ──────────────────────────────────────────


def _is_due(alert: dict, now: datetime) -> bool:
    last_run = alert.get("last_run")
    if last_run is None:
        return True
    try:
        last_dt = datetime.fromisoformat(last_run)
        elapsed = (now - last_dt).total_seconds()
        return elapsed >= alert.get("interval_minutes", 60) * 60
    except ValueError:
        return True


async def _check_alerts() -> None:
    alerts = load_alerts()
    if not alerts:
        return

    now = datetime.now(UTC)
    changed = False

    for alert_id, alert in list(alerts.items()):
        if not _is_due(alert, now):
            continue

        keyword = alert.get("keyword", "?")
        logger.info("Running alert '%s' (id=%s)", keyword, alert_id[:8])

        try:
            new_jobs = await _fetch_new_jobs(alert)
            if new_jobs:
                await _send_notification(alert, new_jobs)
                seen: set[str] = set(alert.get("seen_links", []))
                seen.update(j.link for j in new_jobs)
                # Keep only the most recent entries to limit file size
                alert["seen_links"] = list(seen)[-MAX_SEEN_LINKS:]
                logger.info("Alert '%s': notified %d new jobs", keyword, len(new_jobs))
            else:
                logger.info("Alert '%s': no new jobs", keyword)

            alert["last_run"] = now.isoformat()
            changed = True

        except Exception as e:
            logger.error("Alert '%s' failed: %s", keyword, e)

    if changed:
        save_alerts(alerts)


async def _fetch_new_jobs(alert: dict) -> list[JobListing]:
    """Scrape jobs for the alert and return only unseen ones."""
    from .scraper import scrape_jobs

    request = JobSearchRequest(
        keyword=alert["keyword"],
        pages=alert.get("pages", 3),
        areas=alert.get("areas", []),
        experience=alert.get("experience", []),
    )
    jobs = await scrape_jobs(request)

    min_salary = alert.get("min_salary", 0)
    if min_salary > 0:
        jobs = [j for j in jobs if j.salary_low >= min_salary]

    seen_links: set[str] = set(alert.get("seen_links", []))
    return [j for j in jobs if j.link not in seen_links]


async def _send_notification(alert: dict, new_jobs: list) -> None:
    """Dispatch to the appropriate notification channel."""
    notify_type = alert.get("notify_type", "")
    target = alert.get("notify_target", "")
    keyword = alert.get("keyword", "")

    job_lines = []
    for job in new_jobs[:5]:
        job_lines.append(f"• {job.job} — {job.company} ({job.salary})\n  {job.link}")
    suffix = f"\n\n... 還有 {len(new_jobs) - 5} 筆" if len(new_jobs) > 5 else ""
    message = (
        f"\n🧭 CareerPilot 職缺提醒\n"
        f"關鍵字：{keyword}\n"
        f"找到 {len(new_jobs)} 筆新職缺\n\n" + "\n\n".join(job_lines) + suffix
    )

    if notify_type == "line":
        await _notify_line(target, message)
    elif notify_type == "webhook":
        await _notify_webhook(
            target,
            keyword=keyword,
            count=len(new_jobs),
            message=message,
            jobs=[j.model_dump() for j in new_jobs[:5]],
        )
    else:
        logger.warning("Unknown notify_type: %s", notify_type)


async def _notify_line(token: str, message: str) -> None:
    async with aiohttp.ClientSession() as session:
        resp = await session.post(
            "https://notify-api.line.me/api/notify",
            headers={"Authorization": f"Bearer {token}"},
            data={"message": message},
        )
        if resp.status != 200:
            body = await resp.text()
            logger.error("Line Notify failed (%d): %s", resp.status, body)


async def _notify_webhook(url: str, **payload) -> None:
    async with aiohttp.ClientSession() as session:
        resp = await session.post(url, json=payload)
        if resp.status not in (200, 201, 204):
            body = await resp.text()
            logger.error("Webhook failed (%d): %s", resp.status, body)
