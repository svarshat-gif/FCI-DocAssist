import logging

from apscheduler.schedulers.background import BackgroundScheduler

from crawler.fci_crawler import FciCrawler
from database.session import SessionLocal
from services.upload_service import UploadService
from utils.config import get_settings

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    settings = get_settings()
    if not settings.scheduler_enabled:
        logger.info("Scheduler disabled by configuration.")
        return
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
    _scheduler.add_job(
        run_crawler_job,
        trigger="cron",
        hour=settings.crawler_daily_cron_hour,
        id="daily_fci_crawler",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.add_job(
        cleanup_uploads_job,
        trigger="interval",
        minutes=15,
        id="cleanup_temp_uploads",
        replace_existing=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Scheduler started.")


def shutdown_scheduler() -> None:
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)


def run_crawler_job() -> None:
    with SessionLocal() as db:
        result = FciCrawler(db).run()
        logger.info(
            "Crawler finished: discovered=%s indexed=%s skipped=%s errors=%s",
            result.discovered,
            result.indexed,
            result.skipped,
            len(result.errors),
        )


def cleanup_uploads_job() -> None:
    with SessionLocal() as db:
        count = UploadService(db).cleanup_expired()
        if count:
            logger.info("Cleaned up %s expired upload sessions.", count)
