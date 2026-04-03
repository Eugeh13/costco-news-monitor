"""
Monitoring pipeline — orchestrates the full news monitoring cycle.

This is the "use case" that coordinates all services.
It ONLY orchestrates; it contains NO business logic of its own.

All dependencies are injected through the constructor.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytz

from app.config.keywords import check_high_impact
from app.domain.models import NewsItem
from app.domain.ports import DeepReader, DuplicateChecker, NewsRepository, NewsSource, Notifier
from app.services.content_hasher import ContentHasher
from app.services.deep_analysis import DeepAnalysisService
from app.services.triage import TriageService

CENTRAL_TZ = pytz.timezone("America/Chicago")


class MonitoringPipeline:
    """
    Orchestrates the full monitoring cycle:

    Collect → Hash check → Time filter → Dedup → Triage IA → Deep analysis → Notify
    """

    def __init__(
        self,
        sources: list[NewsSource],
        triage: TriageService,
        deep: DeepAnalysisService,
        notifier: Notifier,
        repository: NewsRepository | None,
        file_storage: DuplicateChecker,
        hasher: ContentHasher,
        max_age_hours: int = 1,
    ) -> None:
        self._sources = sources
        self._triage = triage
        self._deep = deep
        self._notifier = notifier
        self._repo = repository
        self._storage = file_storage
        self._hasher = hasher
        self._max_age_hours = max_age_hours

    def run_once(self) -> None:
        """Execute a single monitoring cycle."""
        now = datetime.now(CENTRAL_TZ)
        print(f"\n🔍 Monitoreo — {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print("=" * 70)

        # ── STEP 1: Collect ──
        print("\n📡 PASO 1: Recolectando noticias...")
        all_news = self._collect()

        if not all_news:
            print("  ⚠️ No se obtuvieron noticias")
            self._send_summary(0, 0, 0, 0)
            return

        # ── STEP 2: Hash check (0 tokens) ──
        print(f"\n🔗 PASO 2: Verificando cambios (hash)...")
        if not self._hasher.has_changed(all_news):
            n = self._hasher.consecutive_no_change
            print(f"  ⚡ Sin cambios ({n}x consecutivo) — 0 tokens consumidos")
            return

        # ── STEP 3: Time filter (0 tokens) ──
        print(f"\n⏰ PASO 3: Filtrando por tiempo ({self._max_age_hours}h)...")
        recent = self._filter_by_time(all_news)
        print(f"  → {len(recent)} noticias recientes de {len(all_news)} totales")

        if not recent:
            print("  ℹ️ No hay noticias recientes")
            self._send_summary(len(all_news), 0, 0, 0)
            return

        # ── STEP 4: Dedup (0 tokens) ──
        print(f"\n🔄 PASO 4: Filtrando duplicadas/procesadas...")
        new_news = self._filter_duplicates(recent)
        print(f"  → {len(new_news)} noticias nuevas de {len(recent)} recientes")

        if not new_news:
            print("  ℹ️ Todas ya procesadas")
            self._send_summary(len(all_news), len(recent), 0, 0)
            return

        # ── STEP 4.5: Keyword hints (soft, not a filter) ──
        keyword_hits = 0
        for item in new_news:
            is_hit, category = check_high_impact(item.titulo)
            if is_hit:
                keyword_hits += 1
                item.keyword_hint = category

        if keyword_hits > 0:
            print(f"\n🔑 {keyword_hits}/{len(new_news)} noticias con keywords de alto impacto")

        # ── STEP 5: AI Triage (batch) ──
        print(f"\n🤖 PASO 5: Triage IA (batch de {len(new_news)} noticias)...")
        candidates = self._triage.triage(new_news)
        print(f"  → {len(candidates)} candidatas identificadas")

        if not candidates:
            print("  ℹ️ Sin candidatas relevantes")
            self._send_summary(len(all_news), len(recent), len(new_news), 0)
            return

        # ── STEP 6: Deep analysis + geo + notify ──
        print(f"\n🔬 PASO 6: Análisis profundo ({len(candidates)} candidatas)...")
        alerts_sent = 0

        for news_item, triage in candidates:
            alert = self._deep.analyze(news_item, triage)

            if alert:
                # Notify
                self._notifier.send_alert(alert)
                print("     📱 Alerta enviada")

                # Persist
                if self._repo:
                    self._repo.save_incident(alert)

                # Mark as processed
                if alert.news.url:
                    self._storage.mark_processed(alert.news.url)

                alerts_sent += 1

        # ── Summary ──
        self._send_summary(len(all_news), len(recent), len(new_news), alerts_sent)

    # ── Private helpers ──────────────────────────────────────

    def _collect(self) -> list[NewsItem]:
        """Collect from all sources."""
        all_items: list[NewsItem] = []

        for source in self._sources:
            try:
                print(f"  📡 {source.source_name()}...")
                items = source.collect()
                print(f"    → {len(items)} noticias")
                all_items.extend(items)
            except Exception as e:
                print(f"    ⚠️ Error: {e}")

        return all_items

    def _filter_by_time(self, news: list[NewsItem]) -> list[NewsItem]:
        """Keep only articles within the time window."""
        cutoff = datetime.now(CENTRAL_TZ) - timedelta(hours=self._max_age_hours)
        recent = []

        for item in news:
            if item.fecha_pub:
                pub = item.fecha_pub
                if pub.tzinfo is None:
                    pub = CENTRAL_TZ.localize(pub)
                if pub >= cutoff:
                    recent.append(item)
            else:
                # No date → let it through (AI will evaluate)
                recent.append(item)

        return recent

    def _filter_duplicates(self, news: list[NewsItem]) -> list[NewsItem]:
        """Remove already-processed and DB-duplicate articles."""
        new_items: list[NewsItem] = []

        for item in news:
            # Check file-based dedup
            if item.url and self._storage.is_processed(item.url):
                continue

            # Check DB dedup
            if self._repo:
                if self._repo.is_duplicate(item.titulo, item.url or "", item.fuente):
                    continue

            new_items.append(item)

        return new_items

    def _send_summary(self, total: int, recent: int, new: int, alerts: int) -> None:
        """Send monitoring summary (only if no alerts were sent)."""
        if alerts > 0:
            return  # Individual alerts are sufficient

        self._notifier.send_summary({
            "timestamp": datetime.now(CENTRAL_TZ).strftime("%d/%m/%Y %H:%M %Z"),
            "news_analyzed": total,
            "alerts_sent": alerts,
        })
