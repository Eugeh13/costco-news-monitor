"""
Smart scheduler — runs the monitoring pipeline with dynamic intervals.

- If no changes → wait longer (up to max_poll_interval)
- If new content → reset to min_poll_interval
- Night pause (23:00 - 06:00 CST)
- A2: ninguna excepción de ciclo mata el loop; cada ciclo registra un
  latido en app.infrastructure.heartbeat para que /health detecte un
  worker muerto y Railway reinicie.
- M8: una vez al día limpia el archivo de URLs procesadas (FileStorage).
- Digest mensual SESNSP: a partir del día crime_digest_day (9:00 hora del
  centro) genera y envía el contexto delictivo; marcador persistente
  YYYY-MM para no reenviar tras un reinicio del contenedor.
"""

import os
import time
import traceback
from datetime import datetime, timedelta

import pytz

from app.config.settings import settings
from app.infrastructure import heartbeat
from crime_report import generar_digest
from main import build_pipeline

CENTRAL_TZ = pytz.timezone("America/Chicago")

# Tope del archivo de procesadas: con el dedup de Fase 1 se marca TODO lo
# triageado, así que el archivo crece rápido. 5000 URLs cubren varios días
# de feeds con margen (el filtro de 1h + dedup en DB cubren el resto).
PROCESSED_FILE_MAX_ENTRIES = 5000


def is_night_time() -> bool:
    hour = datetime.now(CENTRAL_TZ).hour
    return hour >= settings.night_pause_start or hour < settings.night_pause_end


def _daily_cleanup(pipeline) -> None:
    """M8: limpia el archivo de URLs procesadas (FileStorage.cleanup)."""
    storage = getattr(pipeline, "_storage", None)
    if storage is None or not hasattr(storage, "cleanup"):
        return
    removed = storage.cleanup(max_entries=PROCESSED_FILE_MAX_ENTRIES)
    if removed:
        print(f"🧹 Limpieza diaria: {removed} URLs antiguas eliminadas de {settings.processed_news_file}")
    else:
        print("🧹 Limpieza diaria: nada que limpiar")


# ── Digest mensual SESNSP ────────────────────────────────────


def _digest_marker_path() -> str:
    """Marcador 'YYYY-MM' en el mismo directorio de datos que FileStorage,
    para que sobreviva reinicios del contenedor igual que las URLs procesadas."""
    data_dir = os.path.dirname(settings.processed_news_file) or "."
    return os.path.join(data_dir, "crime_digest_sent.txt")


def _digest_already_sent(month_key: str) -> bool:
    try:
        with open(_digest_marker_path(), encoding="utf-8") as f:
            return f.read().strip() == month_key
    except OSError:
        return False  # sin marcador (primer mes o volumen nuevo) → no enviado


def _mark_digest_sent(month_key: str) -> None:
    try:
        with open(_digest_marker_path(), "w", encoding="utf-8") as f:
            f.write(f"{month_key}\n")
    except OSError as e:
        print(f"  ⚠️ No se pudo escribir el marcador del digest: {e}")


def _maybe_send_crime_digest(pipeline, now: datetime) -> None:
    """
    Digest mensual de criminalidad: corre a partir del día crime_digest_day
    a las 9:00 (hora del centro), una sola vez por mes.

    - Se usa `>=` en el día: si el portal SESNSP falla todo el día 25, se
      sigue reintentando los días siguientes hasta lograrlo.
    - Si el portal o el envío fallan, NO se escribe el marcador: se
      reintenta en el siguiente ciclo. Nada de aquí propaga excepciones
      (no debe tumbar ni retrasar el loop de monitoreo).
    - Se llama solo fuera de la pausa nocturna (y además exige hora >= 9).
    """
    if not settings.crime_digest_enabled:
        return
    if now.day < settings.crime_digest_day or now.hour < 9:
        return

    month_key = now.strftime("%Y-%m")
    if _digest_already_sent(month_key):
        return

    try:
        print(f"\n📊 Generando digest mensual SESNSP ({month_key})...")
        digest = generar_digest()
        if digest is None:
            print("  ⚠️ Digest mensual: sin filas del SESNSP — reintento en el siguiente ciclo")
            return

        # Mismo notifier del pipeline: TelegramNotifier si está configurado,
        # ConsoleNotifier (imprime a consola) si no.
        notifier = getattr(pipeline, "_notifier", None)
        if notifier is None:
            print(digest)
        elif not notifier.send_text(digest):
            print("  ⚠️ Digest mensual: el envío falló — reintento en el siguiente ciclo")
            return

        _mark_digest_sent(month_key)
        print(f"  ✓ Digest mensual {month_key} enviado")
    except Exception as e:
        print(f"  ⚠️ Digest mensual falló: {e} — reintento en el siguiente ciclo")
        traceback.print_exc()


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

    heartbeat.register_worker()

    # El pipeline se construye dentro del loop: si falla el arranque
    # (DB caída, import roto), se reintenta en el siguiente ciclo en vez
    # de matar el hilo del worker.
    pipeline = None
    current_interval = min_secs
    last_cleanup_date = None

    try:
        while True:
            sleep_secs = current_interval

            try:
                now = datetime.now(CENTRAL_TZ)

                # Night mode
                if is_night_time():
                    wake_hour = settings.night_pause_end
                    wake_time = now.replace(hour=wake_hour, minute=0, second=0)
                    if now.hour >= settings.night_pause_start:
                        wake_time += timedelta(days=1)

                    wait_secs = max((wake_time - now).total_seconds(), 60)
                    h, m = int(wait_secs // 3600), int((wait_secs % 3600) // 60)
                    print(f"\n🌙 Modo nocturno — {h}h {m}min hasta {wake_time.strftime('%H:%M')}")
                    sleep_secs = wait_secs

                else:
                    if pipeline is None:
                        pipeline = build_pipeline()

                    # Run pipeline
                    print(f"\n{'='*70}")
                    print(f"🔔 {now.strftime('%Y-%m-%d %H:%M:%S %Z')} | Intervalo: {current_interval // 60}min")
                    print(f"{'='*70}")

                    pipeline.run_once()

                    # Adjust interval
                    if pipeline._hasher.consecutive_no_change > 0:
                        current_interval = min(current_interval + step_increase, max_secs)
                        print(f"\n⏱️  Sin cambios → próximo: {current_interval // 60}min")
                    else:
                        current_interval = min_secs
                        print(f"\n⏱️  Contenido nuevo → intervalo: {current_interval // 60}min")

                    sleep_secs = current_interval

                    # M8: limpieza diaria del archivo de procesadas
                    if last_cleanup_date != now.date():
                        _daily_cleanup(pipeline)
                        last_cleanup_date = now.date()

                    # Digest mensual SESNSP (solo corre fuera de la pausa
                    # nocturna porque está dentro de este else; nunca propaga)
                    _maybe_send_crime_digest(pipeline, now)

            except Exception as e:
                # A2: NINGUNA excepción de ciclo mata el worker —
                # log + latido + continuar al siguiente ciclo.
                print(f"\n⚠️ Error en ciclo: {e}")
                traceback.print_exc()
                heartbeat.record_error(f"{type(e).__name__}: {e}")
                sleep_secs = current_interval

            heartbeat.beat(sleep_secs)
            time.sleep(sleep_secs)

    except KeyboardInterrupt:
        print("\n\n🛑 Detenido por el usuario")


if __name__ == "__main__":
    main()
