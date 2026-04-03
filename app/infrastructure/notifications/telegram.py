"""
Telegram notifier — formats and sends alerts to Telegram.

Single responsibility: take domain Alert objects → send formatted messages.
"""

from __future__ import annotations

from datetime import datetime

import requests

from app.domain.models import Alert
from app.domain.ports import Notifier


class TelegramNotifier(Notifier):
    """Sends alerts and summaries to a Telegram chat."""

    def __init__(self, bot_token: str, chat_id: str) -> None:
        self._token = bot_token
        self._chat_id = chat_id
        self._api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    def send_alert(self, alert: Alert) -> bool:
        message = self._format_alert(alert)
        return self._send(message, disable_preview=False)

    def send_summary(self, stats: dict) -> bool:
        message = self._format_summary(stats)
        return self._send(message, disable_preview=True)

    def send_test(self) -> bool:
        message = (
            "🤖 *Test del Sistema de Monitoreo*\n\n"
            "✓ Sistema con IA funcionando correctamente\n"
            "✓ Notificaciones operativas\n\n"
            f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        )
        return self._send(message)

    # ── Formatting ───────────────────────────────────────────

    @staticmethod
    def _format_alert(alert: Alert) -> str:
        a = alert.analysis
        p = alert.proximity

        severity = a.severity
        if severity >= 9:
            severity_label = "CRÍTICA"
        elif severity >= 7:
            severity_label = "GRAVE"
        elif severity >= 5:
            severity_label = "MODERADA"
        else:
            severity_label = "MENOR"

        lines = [
            f"{alert.severity_emoji} *ALERTA COSTCO MTY*\n",
            f"📍 *{alert.category_label}*",
            f"📰 {alert.news.titulo}\n",
            f"⚡ *Severidad: {severity_label}* ({severity}/10)",
        ]

        if a.victims > 0:
            lines.append(f"👥 Víctimas/Heridos: {a.victims}")

        impact_labels = {"high": "*ALTO*", "medium": "Moderado", "low": "Bajo"}
        impact_str = impact_labels.get(a.traffic_impact.value)
        if impact_str:
            lines.append(f"🚗 Impacto en tráfico: {impact_str}")

        if a.emergency_services:
            lines.append("🚑 Servicios de emergencia en el lugar")

        lines.append(f"\n📏 A *{p.distancia_km} km* de {p.costco_nombre}")
        lines.append(f"🗺️ {a.location.extracted}")

        if a.summary:
            lines.append(f"\n📝 {a.summary}")

        lines.append(f"\n📡 {alert.news.fuente}")

        if alert.news.url:
            lines.append(f"🔗 [Ver noticia completa]({alert.news.url})")

        lines.append(f"\n⏰ {alert.timestamp.strftime('%d/%m/%Y %H:%M')}")

        return "\n".join(lines)

    @staticmethod
    def _format_summary(stats: dict) -> str:
        timestamp = stats.get("timestamp", datetime.now().strftime("%d/%m/%Y %H:%M"))
        analyzed = stats.get("news_analyzed", 0)
        alerts = stats.get("alerts_sent", 0)

        lines = [
            "✅ *Monitoreo Completado*\n",
            "📊 *Resumen:*",
            f"• Noticias analizadas: {analyzed}",
            f"• Alertas de alto impacto: {alerts}",
        ]

        if alerts == 0:
            lines.append("• Estado: Todo tranquilo ✓")

        lines.append(f"\n⏰ {timestamp}")
        return "\n".join(lines)

    # ── Transport ────────────────────────────────────────────

    def _send(self, text: str, disable_preview: bool = True) -> bool:
        try:
            response = requests.post(
                self._api_url,
                json={
                    "chat_id": self._chat_id,
                    "text": text,
                    "parse_mode": "Markdown",
                    "disable_web_page_preview": disable_preview,
                },
                timeout=10,
            )

            if response.status_code == 200:
                print("  ✓ Telegram: mensaje enviado")
                return True

            print(f"  ⚠️ Telegram error: {response.status_code}")
            return False

        except Exception as e:
            print(f"  ⚠️ Telegram error: {e}")
            return False


class ConsoleNotifier(Notifier):
    """Fallback notifier that prints to console when Telegram is not configured."""

    def send_alert(self, alert: Alert) -> bool:
        print(f"\n{'='*70}")
        print(f"🚨 ALERTA: {alert.category_label}")
        print(f"📰 {alert.news.titulo}")
        print(f"📍 {alert.analysis.location.extracted}")
        print(f"📏 {alert.proximity.distancia_km} km de {alert.proximity.costco_nombre}")
        print(f"⚡ Severidad: {alert.analysis.severity}/10")
        print(f"{'='*70}\n")
        return True

    def send_summary(self, stats: dict) -> bool:
        print(f"  📊 Resumen: {stats.get('news_analyzed', 0)} analizadas, "
              f"{stats.get('alerts_sent', 0)} alertas")
        return True
