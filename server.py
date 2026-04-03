"""
Server — runs FastAPI + monitoring worker in parallel.

For Railway: `web: python server.py`
"""

import asyncio
import threading

import uvicorn

from app.config.settings import settings


def run_worker():
    """Run the monitoring scheduler in a background thread."""
    from scheduler import main as scheduler_main
    try:
        scheduler_main()
    except Exception as e:
        print(f"⚠️ Worker error: {e}")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║  Costco News Monitor — Server Mode                               ║
║  API + Worker running in parallel                                ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    # Start worker in background thread
    worker_thread = threading.Thread(target=run_worker, daemon=True)
    worker_thread.start()
    print("✓ Worker thread started")

    # Start FastAPI in main thread
    port = int(settings.model_extra.get("PORT", 8000)) if settings.model_extra else 8000
    import os
    port = int(os.environ.get("PORT", 8000))

    print(f"✓ API starting on port {port}")
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
