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
from typing import Optional

from app.config.settings import settings
from app.infrastructure.notifications.telegram import ConsoleNotifier, TelegramNotifier
from app.infrastructure.sources.sesnsp_municipal import SESNSPMunicipalData
from app.services.crime_digest import MUNICIPIOS_COSTCO, CrimeDigestService


def generar_digest(url: Optional[str] = None, csv_path: Optional[str] = None) -> Optional[str]:
    """
    Descarga los datos del SESNSP y devuelve el texto del digest.

    Reutilizable: la usa este CLI y el digest mensual programado del
    scheduler. Devuelve None si el portal no entregó filas (caído o sin
    datos), para que el scheduler reintente sin marcar el mes como enviado.
    """
    source = SESNSPMunicipalData()
    rows = source.fetch_rows(
        claves_municipio=list(MUNICIPIOS_COSTCO.keys()),
        url=url,
        local_path=csv_path,
    )
    print(f"  ✓ {len(rows)} filas de {len(MUNICIPIOS_COSTCO)} municipios")
    if not rows:
        return None
    return CrimeDigestService().build(rows)


def main():
    parser = argparse.ArgumentParser(description="Digest mensual de criminalidad SESNSP")
    parser.add_argument("--csv", help="Ruta a un CSV municipal ya descargado (opcional)")
    parser.add_argument("--url", help="URL directa del CSV (opcional; si no, se descubre)")
    parser.add_argument("--telegram", action="store_true", help="Enviar por Telegram")
    args = parser.parse_args()

    digest = generar_digest(url=args.url, csv_path=args.csv)
    if digest is None:
        # Mismo texto que producía CrimeDigestService.build([]) antes del
        # refactor: el CLI manual se comporta idéntico.
        digest = "⚠️ Sin datos del SESNSP para generar el digest."

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
