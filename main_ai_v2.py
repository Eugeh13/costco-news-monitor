"""
Script principal v2 del sistema de monitoreo de noticias.

CAMBIOS vs v1:
- Scraper multi-fuente (Google News RSS + GNews + RSS directo + Crawl4AI)
- Triage por batch (1 llamada IA para ~50 noticias vs 50 llamadas)
- Análisis profundo solo para candidatas (~5-10% del total)
- Soporte configurable para OpenAI/Anthropic
- ~70% menos llamadas a IA = ~70% menos costo

Compatible con: config.py, geolocation.py, notifier_ai.py, storage.py, database.py
"""

import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional

import pytz

# Zona horaria
CENTRAL_TZ = pytz.timezone('America/Chicago')

# Módulos locales (existentes, sin cambios)
import config
from analyzer import NewsAnalyzer
from geolocation import GeoLocator
from notifier_ai import NotifierAI as Notifier
from storage import NewsStorage
from time_filter import TimeFilter
from database import NewsDatabase

# Módulos NUEVOS
from scraper_v3 import NewsScraperV3, NewsItem
from ai_analyzer_v2 import AIAnalyzerV2, create_analyzer, TriageResult


class NewsMonitorV2:
    """
    Sistema de monitoreo v2 con scraping multi-fuente y triage IA.
    
    Pipeline:
    1. RECOLECTAR: Noticias de Google News RSS + GNews + RSS directo
    2. FILTRAR TIEMPO: Solo noticias de última hora
    3. TRIAGE IA (batch): 1 llamada clasifica todo el batch
    4. LECTURA PROFUNDA: Solo candidatas → Crawl4AI extrae artículo completo
    5. ANÁLISIS PROFUNDO: IA analiza contenido completo
    6. GEOCODIFICAR: Verificar proximidad a Costco
    7. NOTIFICAR: Telegram + PostgreSQL
    """
    
    def __init__(self):
        print("Inicializando sistema de monitoreo v2...")
        print()
        
        # === Módulos nuevos ===
        self.scraper = NewsScraperV3()
        self.ai = create_analyzer()
        
        # === Módulos existentes (sin cambios) ===
        self.analyzer = NewsAnalyzer(config.KEYWORDS)  # Pre-filtro por keywords
        self.time_filter = TimeFilter(max_age_hours=1)
        self.geolocator = GeoLocator()
        self.notifier = Notifier(config.NOTIFICATION_CONFIG)
        self.storage = NewsStorage(config.PROCESSED_NEWS_FILE)
        self.database = NewsDatabase()
        self.costco_locations = config.COSTCO_LOCATIONS
        self.radius_km = config.RADIUS_KM
        
        print()
        print("✓ Sistema v2 inicializado")
        print(f"  Pipeline: Multi-source → Triage IA → Deep analysis → Geo → Telegram")
        print()
    
    # ========================================================
    # Pipeline principal
    # ========================================================
    
    def monitor_sources(self):
        """Ejecuta el pipeline completo de monitoreo."""
        timestamp = datetime.now(CENTRAL_TZ)
        
        print(f"\n{'='*70}")
        print(f"🔍 Monitoreo v2 - {timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        print(f"{'='*70}\n")
        
        # ── PASO 1: Recolectar de todas las fuentes ──
        print("📡 PASO 1: Recolectando noticias de múltiples fuentes...")
        all_news = self.scraper.collect_all_news()
        
        if not all_news:
            print("  ⚠️ No se encontraron noticias en ninguna fuente")
            self._send_summary(0, 0, 0, 0)
            return
        
        # ── PASO 2: Filtrar por tiempo ──
        print(f"\n⏰ PASO 2: Filtrando por tiempo (última hora)...")
        recent_news = self._filter_recent(all_news)
        print(f"  → {len(recent_news)} noticias recientes de {len(all_news)} totales")
        
        if not recent_news:
            print("  ℹ️ No hay noticias recientes")
            self._send_summary(len(all_news), 0, 0, 0)
            return
        
        # ── PASO 3: Filtrar ya procesadas y duplicadas ──
        print(f"\n🔄 PASO 3: Filtrando duplicadas/procesadas...")
        new_news = self._filter_processed(recent_news)
        print(f"  → {len(new_news)} noticias nuevas de {len(recent_news)} recientes")
        
        if not new_news:
            print("  ℹ️ Todas las noticias ya fueron procesadas")
            self._send_summary(len(all_news), len(recent_news), 0, 0)
            return
        
        # ── PASO 4: Triage IA (batch) ──
        print(f"\n🤖 PASO 4: Triage IA (batch de {len(new_news)} noticias)...")
        candidates = self._batch_triage(new_news)
        print(f"  → {len(candidates)} candidatas identificadas")
        
        if not candidates:
            print("  ℹ️ Ninguna noticia pasó el triage")
            self._send_summary(len(all_news), len(recent_news), len(new_news), 0)
            return
        
        # ── PASO 5: Análisis profundo + geo + notificación ──
        print(f"\n🔬 PASO 5: Análisis profundo de {len(candidates)} candidatas...")
        alerts_sent = 0
        
        for news_item, triage in candidates:
            result = self._process_candidate(news_item, triage)
            if result:
                alerts_sent += 1
            time.sleep(1)  # Rate limiting entre candidatas
        
        # ── Resumen ──
        self._send_summary(len(all_news), len(recent_news), len(new_news), alerts_sent)
        
        print(f"\n{'='*70}")
        print(f"✓ Monitoreo completado")
        print(f"  Recolectadas: {len(all_news)} | Recientes: {len(recent_news)} | "
              f"Nuevas: {len(new_news)} | Candidatas: {len(candidates)} | Alertas: {alerts_sent}")
        print(f"{'='*70}\n")
    
    # ========================================================
    # Funciones del pipeline
    # ========================================================
    
    def _filter_recent(self, news: List[NewsItem]) -> List[NewsItem]:
        """Filtra solo noticias de la última hora."""
        recent = []
        for item in news:
            # Usar el filtro de tiempo existente
            item_dict = item.to_dict()
            is_recent, reason = self.time_filter.filter_news_item(item_dict)
            if is_recent:
                recent.append(item)
        return recent
    
    def _filter_processed(self, news: List[NewsItem]) -> List[NewsItem]:
        """Filtra noticias ya procesadas o duplicadas."""
        new_items = []
        for item in news:
            # Verificar archivo local
            if item.url and self.storage.is_processed(item.url):
                continue
            # Verificar base de datos
            if self.database.enabled:
                if self.database.is_duplicate(item.titulo, item.url, item.fuente, max_hours=24):
                    continue
            new_items.append(item)
        return new_items
    
    def _batch_triage(self, news: List[NewsItem]) -> List[tuple]:
        """
        Ejecuta triage IA en batch.
        
        Returns:
            Lista de tuplas (NewsItem, TriageResult) para candidatas
        """
        # Preparar batch para triage
        batch = [item.to_dict() for item in news]
        
        # Dividir en chunks de máx 25 para evitar que el JSON se corte
        CHUNK_SIZE = 25
        all_triage_results = []
        
        for chunk_start in range(0, len(batch), CHUNK_SIZE):
            chunk = batch[chunk_start:chunk_start + CHUNK_SIZE]
            # Reindexar el chunk desde 0
            for i, item in enumerate(chunk):
                item['_chunk_index'] = i
            
            chunk_results = self.ai.batch_triage(chunk)
            
            # Restaurar el índice global
            for result in chunk_results:
                result.index = chunk_start + result.index
                all_triage_results.append(result)
        
        # Emparejar resultados con noticias originales
        candidates = []
        for triage in all_triage_results:
            if triage.is_candidate and triage.index < len(news):
                candidates.append((news[triage.index], triage))
        
        return candidates
    
    def _process_candidate(self, news_item: NewsItem, triage: TriageResult) -> bool:
        """
        Procesa una noticia candidata: lectura profunda → análisis IA → geo → notificación.
        
        Returns:
            True si se envió alerta
        """
        titulo = news_item.titulo
        url = news_item.url
        fuente = news_item.fuente
        
        print(f"\n  📰 Procesando: {titulo[:70]}...")
        print(f"     Triage: {triage.estimated_category} | Sev ~{triage.estimated_severity} | {triage.location_hint}")
        
        # ── Lectura profunda del artículo ──
        print(f"     📖 Extrayendo artículo completo...")
        content = news_item.contenido  # Default: snippet
        
        if url:
            full_content = self.scraper.get_article_content(url)
            if full_content and len(full_content) > len(content):
                content = full_content
                print(f"     ✓ Artículo completo: {len(content)} chars")
            else:
                print(f"     ⚠️ Usando snippet ({len(content)} chars)")
        
        # ── Análisis profundo con IA ──
        print(f"     🤖 Análisis profundo...")
        analysis = self.ai.deep_analyze(titulo, content)
        
        if not analysis:
            print(f"     ⚠️ Error en análisis IA")
            return False
        
        if not analysis.get('is_relevant', False):
            reason = analysis.get('exclusion_reason', 'No relevante')
            print(f"     ❌ Descartada: {reason}")
            return False
        
        severity = analysis.get('severity', 5)
        category = analysis.get('category', triage.estimated_category)
        print(f"     ✓ Relevante | {category} | Severidad: {severity}/10")
        
        # ── Verificar ubicación ──
        location_info = analysis.get('location', {})
        location_text = location_info.get('extracted')
        is_specific = location_info.get('is_specific', False)
        
        if not location_text or not is_specific:
            print(f"     ⚠️ Ubicación no específica")
            return False
        
        print(f"     📍 Ubicación: {location_text}")
        
        # ── Geocodificar ──
        normalized = location_info.get('normalized', location_text)
        coords = self.geolocator.geocode_location(normalized + ", Monterrey, NL")
        
        if not coords:
            coords = self.geolocator.geocode_location(location_text + ", Monterrey, NL")
        
        if not coords:
            print(f"     ⚠️ No se pudo geocodificar")
            return False
        
        print(f"     🗺️ Coords: {coords[0]:.6f}, {coords[1]:.6f}")
        
        # ── Verificar radio de Costco ──
        is_within, nearest_costco = self.geolocator.is_within_radius(
            coords, self.costco_locations, self.radius_km
        )
        
        # Verificar vialidades clave
        if not is_within:
            is_within, nearest_costco = self._check_key_roads(
                content, coords, nearest_costco
            )
        
        if not is_within:
            print(f"     ❌ Fuera del radio ({nearest_costco['distancia_km']} km)")
            return False
        
        print(f"     ✓ Dentro del radio: {nearest_costco['distancia_km']} km de {nearest_costco['nombre']}")
        
        # ── Notificar ──
        self._send_alert(news_item, analysis, nearest_costco, coords)
        
        # ── Guardar ──
        self._save_to_db(news_item, analysis, nearest_costco, coords)
        
        if url:
            self.storage.mark_as_processed(url)
        
        return True
    
    def _check_key_roads(self, content: str, coords, nearest_costco) -> tuple:
        """Verifica si la noticia menciona vialidades clave de algún Costco."""
        content_lower = content.lower()
        
        for costco_name, costco_data in self.costco_locations.items():
            vialidades = costco_data.get('vialidades_clave', [])
            for vialidad in vialidades:
                if vialidad in content_lower:
                    print(f"     ✓ Vialidad clave: '{vialidad}' ({costco_name})")
                    costco_coords = (costco_data['lat'], costco_data['lon'])
                    distancia = self.geolocator.calculate_distance(coords, costco_coords)
                    return True, {
                        'nombre': costco_name,
                        'direccion': costco_data['direccion'],
                        'distancia_km': round(distancia, 2)
                    }
        
        return False, nearest_costco
    
    def _send_alert(self, news_item: NewsItem, analysis: dict, 
                    nearest_costco: dict, coords: tuple):
        """Envía notificación de alerta a Telegram."""
        severity = analysis.get('severity', 5)
        details = analysis.get('details', {})
        
        if severity >= 9:
            severity_emoji = "🚨🚨"
        elif severity >= 7:
            severity_emoji = "🚨"
        elif severity >= 5:
            severity_emoji = "⚠️"
        else:
            severity_emoji = "ℹ️"
        
        notification_data = {
            'categoria': self.analyzer.extract_category_label(
                analysis.get('category', 'otro')
            ),
            'titulo': news_item.titulo,
            'ubicacion': analysis['location']['extracted'],
            'distancia_km': nearest_costco['distancia_km'],
            'costco_cercano': nearest_costco['nombre'],
            'costco_direccion': nearest_costco['direccion'],
            'fuente': news_item.fuente,
            'url': news_item.url or 'No disponible',
            'resumen': analysis.get('summary', news_item.titulo),
            'severity': severity,
            'severity_emoji': severity_emoji,
            'victims': details.get('victims', 0),
            'traffic_impact': details.get('traffic_impact', 'unknown'),
            'emergency_services': details.get('emergency_services', False),
        }
        
        self.notifier.notify(notification_data)
        print(f"     📱 Alerta enviada a Telegram")
    
    def _save_to_db(self, news_item: NewsItem, analysis: dict,
                    nearest_costco: dict, coords: tuple):
        """Guarda en base de datos PostgreSQL."""
        if not self.database.enabled:
            return
        
        details = analysis.get('details', {})
        
        db_record = {
            'titulo': news_item.titulo,
            'categoria': analysis.get('category', 'desconocido'),
            'url': news_item.url or '',
            'descripcion': analysis.get('summary', ''),
            'costco_nombre': nearest_costco['nombre'],
            'fuente': news_item.fuente,
            'severidad': analysis.get('severity', 5),
            'ubicacion_texto': analysis['location']['extracted'],
            'latitud': coords[0],
            'longitud': coords[1],
            'costco_distancia_km': nearest_costco['distancia_km'],
            'victimas': details.get('victims', 0),
            'heridos': 0,
            'impacto_trafico': details.get('traffic_impact', 'unknown'),
            'servicios_emergencia': details.get('emergency_services', False),
            'fecha_publicacion': getattr(news_item, 'fecha_pub', None),
            'alerta_enviada': True,
        }
        
        self.database.save_noticia(db_record)
        print(f"     💾 Guardada en DB")
    
    def _send_summary(self, total: int, recent: int, new: int, alerts: int):
        """Envía resumen del monitoreo."""
        if alerts > 0:
            return  # Las alertas individuales ya son suficientes
        
        timestamp = datetime.now(CENTRAL_TZ).strftime("%d/%m/%Y %H:%M %Z")
        summary_data = {
            'timestamp': timestamp,
            'news_analyzed': total,
            'alerts_sent': alerts,
        }
        self.notifier.send_monitoring_summary(summary_data)
    
    # ========================================================
    # Ejecución
    # ========================================================
    
    def run_once(self):
        """Ejecuta un ciclo de monitoreo."""
        try:
            self.monitor_sources()
        except Exception as e:
            print(f"❌ Error en monitoreo: {e}")
            import traceback
            traceback.print_exc()
    
    def run_continuous(self, interval_minutes: int = 30):
        """Ejecuta en modo continuo."""
        print(f"Modo continuo: cada {interval_minutes} minutos")
        print("Ctrl+C para detener\n")
        
        try:
            while True:
                self.run_once()
                print(f"⏳ Siguiente monitoreo en {interval_minutes} min...")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n🛑 Detenido")


def main():
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║  Sistema de Monitoreo de Noticias v2                             ║
║  Monterrey, NL — Multi-source + Triage IA                       ║
║                                                                   ║
║  Fuentes: Google News RSS + GNews + RSS directo + Crawl4AI      ║
║  IA: Triage batch + Análisis profundo                            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")
    
    monitor = NewsMonitorV2()
    monitor.run_once()


if __name__ == "__main__":
    main()
