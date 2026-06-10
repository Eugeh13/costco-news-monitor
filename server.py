"""
Server — runs FastAPI + monitoring worker in parallel.

For Railway: `web: python server.py`
"""

import os
import threading
import time

import uvicorn


def run_worker():
    """Run the monitoring scheduler in a background thread."""
    from scheduler import main as scheduler_main
    try:
        scheduler_main()
    except Exception as e:
        print(f"⚠️ Worker error: {e}")


def run_watchdog():
    """Termina el proceso si el worker queda muerto o atorado.

    Railway NO monitorea /health en runtime (solo durante el deploy): el 503
    del endpoint es observabilidad, no recuperación. La única señal que
    dispara el restartPolicyType ON_FAILURE es que el proceso termine — eso
    hace este hilo cuando el heartbeat reporta no-saludable dos chequeos
    seguidos (~4 min), reusando la misma tolerancia que /health (gracia de
    arranque, sueño nocturno planeado + 3x intervalo).
    """
    from app.infrastructure import heartbeat

    fallos_consecutivos = 0
    while True:
        time.sleep(120)
        healthy, status, detail = heartbeat.check()
        if healthy:
            fallos_consecutivos = 0
            continue
        fallos_consecutivos += 1
        print(f"⚠️ Watchdog: worker {status} ({fallos_consecutivos}/2) — {detail}")
        if fallos_consecutivos >= 2:
            print("💀 Watchdog: worker irrecuperable — saliendo para que Railway reinicie el contenedor")
            os._exit(1)


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

    # Watchdog: reinicia el contenedor (vía exit del proceso) si el worker muere
    watchdog_thread = threading.Thread(target=run_watchdog, daemon=True)
    watchdog_thread.start()
    print("✓ Watchdog thread started")

    # Start FastAPI in main thread — Railway inyecta PORT como variable de entorno
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
