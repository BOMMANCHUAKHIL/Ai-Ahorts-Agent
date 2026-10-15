from dotenv import load_dotenv
load_dotenv()
import logging
import config_defaults
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS
from apscheduler.schedulers.blocking import BlockingScheduler
from src.orchestrator import ShortsOrchestrator
# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def job():
    """The scheduled task."""
    try:
        orch = ShortsOrchestrator()
        orch.run_cycle()
    except Exception as e:
        log.error(f"Cycle failed: {e}", exc_info=True)


if __name__ == "__main__":
    log.info("Starting Shorts Agent...")

    # Run once immediately on startup (optional)
    job()

    # Then schedule
    sched = BlockingScheduler()
    sched.add_job(
        job,
        "interval",
        minutes=60,  # every hour
        id="shorts_cycle",
        max_instances=1,  # prevent overlap
        coalesce=True  # if missed, run only once
    )

    log.info("Scheduler running. Ctrl+C to stop.")
    try:
        sched.start()
    except KeyboardInterrupt:
        log.info("Shutting down...")