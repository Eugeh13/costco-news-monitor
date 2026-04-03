"""
Smart scheduler — runs the monitoring pipeline with dynamic intervals.

- If no changes → wait longer (up to max_poll_interval)
- If new content → reset to min_poll_interval
- Night pause (23:00 - 06:00 CST)
"""

import time
from datetime import datetime, timedelta

import pytz

from app.config.settings import settings
from main import build_pipeline

CENTRAL_TZ = pytz.timezone("America/Chicago")


def is_night_time() -> bool:
    hour = datetime.now(CENTRAL_TZ).hour
    return hour >= settings.night_pause_start or hour < settings.night_pause_end


def main():
    min_secs = settings.min_poll_interval_minutes * 60
    max_secs = settings.max_poll_interval_minutes * 60
    step_increase = 2 * 60

    print(f"""
╔═══════════════════════════════════════════════════════════════════╗
║  Costco News Monitor — Smart Scheduler                           ║
║  Intervalo: {settings.min_poll_interval_minutes}-{settings.max_poll_interval_minutes} min | Pausa nocturna: {settings.night_pause_start}:00 - {settings.night_pause_end}:00 CST        ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    pipeline = build_pipeline()
    current_interval = min_secs

    try:
        while True:
            now = datetime.now(CENTRAL_TZ)

            # Night mode
            if is_night_time():
                wake_hour = settings.night_pause_end
                wake_time = now.replace(hour=wake_hour, minute=0, second=0)
                if now.hour >= settings.night_pause_start:
                    wake_time += timedelta(days=1)

                wait_secs = (wake_time - now).total_seconds()
                h, m = int(wait_secs // 3600), int((wait_secs % 3600) // 60)
                print(f"\n🌙 Modo nocturno — {h}h {m}min hasta {wake_time.strftime('%H:%M')}")
                time.sleep(wait_secs)
                continue

            # Run pipeline
            print(f"\n{'='*70}")
            print(f"🔔 {now.strftime('%Y-%m-%d %H:%M:%S %Z')} | Intervalo: {current_interval // 60}min")
            print(f"{'='*70}")

            try:
                pipeline.run_once()

                # Adjust interval
                if pipeline._hasher.consecutive_no_change > 0:
                    current_interval = min(current_interval + step_increase, max_secs)
                    print(f"\n⏱️  Sin cambios → próximo: {current_interval // 60}min")
                else:
                    current_interval = min_secs
                    print(f"\n⏱️  Contenido nuevo → intervalo: {current_interval // 60}min")

            except Exception as e:
                print(f"\n⚠️ Error: {e}")
                import traceback
                traceback.print_exc()

            time.sleep(current_interval)

    except KeyboardInterrupt:
        print("\n\n🛑 Detenido por el usuario")


if __name__ == "__main__":
    main()
