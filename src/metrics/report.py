from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.metrics import aggregators, quality


async def generate_markdown_report(session: AsyncSession) -> str:
    """Build a complete Markdown quality report and return it as a string."""
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    stage_counts = await aggregators.counts_by_stage(session)
    decision_counts = await aggregators.counts_by_final_decision(session)
    latency = await aggregators.avg_latency_ms(session)
    tokens = await aggregators.total_tokens_used(session)
    tph = await aggregators.throughput_per_hour(session)
    by_source = await aggregators.distribution_by_source(session)
    by_type = await aggregators.distribution_by_type(session)
    by_severity = await aggregators.distribution_by_severity(session)

    prec = await quality.precision(session)
    rec = await quality.recall(session)
    acc_stage = await quality.accuracy_by_stage(session)
    errors = await quality.top_error_patterns(session)

    total_articles = sum(stage_counts.values())

    lines: list[str] = []

    lines += [
        f"# Reporte de Calidad — {now}",
        "",
        "## 1. Resumen Ejecutivo",
        "",
        "| Métrica | Valor |",
        "|---------|-------|",
        f"| Total artículos procesados | {total_articles} |",
        f"| Throughput (última 24 h) | {tph:.2f} inc/h |",
        f"| Latencia promedio pipeline | {latency:.0f} ms |",
        f"| Tokens totales consumidos | {tokens['total']:,} |",
        f"| Precisión del clasificador | {prec:.1%} |",
        f"| Recall del clasificador | {rec:.1%} |",
        "",
    ]

    lines += [
        "## 2. Distribución por Etapa del Pipeline",
        "",
        "| Etapa | Count |",
        "|-------|-------|",
    ]
    for stage, cnt in sorted(stage_counts.items()):
        lines.append(f"| {stage} | {cnt} |")
    lines.append("")

    lines += [
        "## 3. Decisiones Finales",
        "",
        "| Decisión | Count |",
        "|----------|-------|",
    ]
    if decision_counts:
        for dec, cnt in sorted(decision_counts.items(), key=lambda x: -x[1]):
            lines.append(f"| {dec} | {cnt} |")
    else:
        lines.append("| *(tabla decision_logs aún no disponible)* | — |")
    lines.append("")

    lines += [
        "## 4. Calidad por Etapa",
        "",
        "| Etapa | Accuracy |",
        "|-------|----------|",
    ]
    if acc_stage:
        for stage, acc in sorted(acc_stage.items()):
            lines.append(f"| {stage} | {acc:.1%} |")
    else:
        lines.append("| *(tabla decision_logs aún no disponible)* | — |")
    lines.append("")

    lines += [
        "## 5. Distribución de Incidentes",
        "",
        "### Por Fuente",
        "",
        "| Fuente | Count |",
        "|--------|-------|",
    ]
    for src, cnt in sorted(by_source.items(), key=lambda x: -x[1]):
        lines.append(f"| {src} | {cnt} |")

    lines += [
        "",
        "### Por Tipo",
        "",
        "| Tipo | Count |",
        "|------|-------|",
    ]
    for t, cnt in sorted(by_type.items(), key=lambda x: -x[1]):
        lines.append(f"| {t} | {cnt} |")

    lines += [
        "",
        "### Por Severidad",
        "",
        "| Severidad | Count |",
        "|-----------|-------|",
    ]
    severity_order = {"critica": 0, "grave": 1, "moderada": 2, "menor": 3}
    for sev, cnt in sorted(by_severity.items(), key=lambda x: severity_order.get(x[0], 99)):
        lines.append(f"| {sev} | {cnt} |")
    lines.append("")

    lines += [
        "## 6. Patrones de Error Más Frecuentes",
        "",
        "| Predicho | Debería ser | Ocurrencias |",
        "|----------|-------------|-------------|",
    ]
    if errors:
        for e in errors:
            lines.append(f"| {e['predicted']} | {e['should_have_been']} | {e['count']} |")
    else:
        lines.append("| *(sin datos de feedback aún)* | — | — |")
    lines.append("")

    lines += [
        "## 7. Consumo de Tokens",
        "",
        "| Tipo | Tokens |",
        "|------|--------|",
        f"| Prompt | {tokens['prompt']:,} |",
        f"| Completion | {tokens['completion']:,} |",
        f"| **Total** | **{tokens['total']:,}** |",
        "",
        "*Generado automáticamente por costco-news-monitor v2*",
    ]

    return "\n".join(lines)
