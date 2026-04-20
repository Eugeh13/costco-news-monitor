#!/usr/bin/env python3
"""CLI: genera REPORTE_CALIDAD.md consultando la base de datos.

Exit codes:
  0 — reporte generado sin problemas
  1 — error de conexión a la base de datos
  2 — error inesperado
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import structlog
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

ROOT = Path(__file__).parent.parent
OUTPUT_FILE = ROOT / "REPORTE_CALIDAD.md"

console = Console()
logger = structlog.get_logger(__name__)


async def _run(output: Path) -> None:
    from src.core.database import get_sessionmaker
    from src.metrics import generate_markdown_report

    session_factory = get_sessionmaker()

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Consultando base de datos…", total=None)
        async with session_factory() as session:
            report_md = await generate_markdown_report(session)

    output.write_text(report_md, encoding="utf-8")
    console.print(f"[bold green]✓[/] Reporte escrito en [cyan]{output}[/]")

    line_count = report_md.count("\n")
    console.print(f"  {line_count} líneas generadas.")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Genera reporte de calidad del pipeline.")
    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_FILE,
        help="Ruta del archivo Markdown de salida (default: REPORTE_CALIDAD.md)",
    )
    args = parser.parse_args()

    try:
        asyncio.run(_run(args.output))
    except OSError as exc:
        console.print(f"[bold red]Error de conexión:[/] {exc}", style="red")
        logger.error("db_connection_error", error=str(exc))
        sys.exit(1)
    except Exception as exc:
        console.print(f"[bold red]Error inesperado:[/] {exc}", style="red")
        logger.exception("unexpected_error", error=str(exc))
        sys.exit(2)


if __name__ == "__main__":
    main()
