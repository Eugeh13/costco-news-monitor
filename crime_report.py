"""
Crime report — genera y envía el digest mensual de incidencia delictiva.

Módulo independiente del pipeline de alertas. Pensado para correrse una vez
al mes (manual o programado), después de que el SESNSP publica (~día 20).

Uso:
    python crime_report.py                  # descarga oficial + imprime en consola
    python crime_report.py --csv data.csv   # usa un CSV local (drop manual / caché)
    python crime_report.py --telegram       # además lo envía por Telegram
"""

import argparse

from app.config.settings import settings
from app.infrastructure.notifications.telegram import ConsoleNotifier, TelegramNotifier
from app.infrastructure.sources.sesnsp_municipal import SESNSPMunicipalData
from app.services.crime_digest import MUNICIPIOS_COSTCO, CrimeDigestService


def main():
    parser = argparse.ArgumentParser(description="Digest mensual de criminalidad SESNSP")
    parser.add_argument("--csv", help="Ruta a un CSV municipal ya descargado (opcional)")
    parser.add_argument("--url", help="URL directa del CSV (opcional; si no, se descubre)")
    parser.add_argument("--telegram", action="store_true", help="Enviar por Telegram")
    args = parser.parse_args()

    source = SESNSPMunicipalData()
    rows = source.fetch_rows(
        claves_municipio=list(MUNICIPIOS_COSTCO.keys()),
        url=args.url,
        local_path=args.csv,
    )
    print(f"  ✓ {len(rows)} filas de {len(MUNICIPIOS_COSTCO)} municipios")

    digest = CrimeDigestService().build(rows)

    if args.telegram and settings.telegram_enabled:
        notifier = TelegramNotifier(
            bot_token=settings.telegram_bot_token,
            chat_id=settings.telegram_chat_id,
        )
    else:
        if args.telegram:
            print("  ⚠️ Telegram no configurado — imprimiendo en consola")
        notifier = ConsoleNotifier()

    notifier.send_text(digest)


if __name__ == "__main__":
    main()
