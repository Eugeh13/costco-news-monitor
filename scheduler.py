#!/usr/bin/env python3
"""
Scheduler para costco-news-monitor v2 en Railway.
Ejecuta el pipeline cada 6 horas en loop infinito.
"""
import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Logging a stdout para que Railway lo capture
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

# Asegurar que el proyecto sea importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

INTERVAL_SECONDS = 21600  # 6 hours - reduced from 2h to optimize Anthropic API costs during validation period


async def run_pipeline_once():
    """Ejecuta una corrida del pipeline. Captura excepciones para no matar el scheduler."""
    log.info("=== Pipeline run starting ===")
    try:
        from scripts.run_pipeline import main as run_pipeline_main
        await run_pipeline_main()
        log.info("=== Pipeline run completed successfully ===")
    except Exception as e:
        log.exception("Pipeline run failed: %s", e)


async def scheduler_loop():
    """Loop infinito que corre el pipeline cada INTERVAL_SECONDS."""
    log.info("Scheduler starting. Interval: %ss (%.1f hours)", INTERVAL_SECONDS, INTERVAL_SECONDS / 3600)

    while True:
        start = datetime.utcnow()
        await run_pipeline_once()

        elapsed = (datetime.utcnow() - start).total_seconds()
        sleep_time = max(0, INTERVAL_SECONDS - elapsed)
        log.info("Next run in %ss (%.1f hours). Sleeping...", int(sleep_time), sleep_time / 3600)
        await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    log.info("costco-news-monitor v2 scheduler starting up")
    try:
        asyncio.run(scheduler_loop())
    except KeyboardInterrupt:
        log.info("Scheduler interrupted, shutting down")
        sys.exit(0)
