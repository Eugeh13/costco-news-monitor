"""
Script principal del sistema de monitoreo de noticias de alto impacto.
VERSIÓN MEJORADA CON ANÁLISIS DE IA (OpenAI)
"""

import time
from datetime import datetime

# Importar módulos locales
import config
from scraper import NewsScraperV2 as NewsScraper
from analyzer import NewsAnalyzer
from ai_analyzer import AINewsAnalyzer
from geolocation import GeoLocator
from notifier_ai import NotifierAI as Notifier
from storage import NewsStorage
from time_filter import TimeFilter

# Importar Twitter scraper con autenticación
try:
    from twitter_scraper_auth import TwitterScraperAuth
    TWITTER_AUTH_AVAILABLE = True
except ImportError:
    TWITTER_AUTH_AVAILABLE = False
    print("⚠️  twitter_scraper_auth no disponible")


class NewsMonitorAI:
    """Clase principal que orquesta el monitoreo de noticias con análisis de IA."""
    
    def __init__(self, use_ai: bool = True):
        """
        Inicializa todos los componentes del sistema.
        
        Args:
            use_ai: Si True, usa análisis con IA. Si False, usa método tradicional.
        """
        print("Inicializando sistema de monitoreo de noticias con IA...")
        
        self.scraper = NewsScraper()
        self.analyzer = NewsAnalyzer(config.KEYWORDS)
        self.ai_analyzer = AINewsAnalyzer() if use_ai else None
        self.time_filter = TimeFilter(max_age_hours=1)  # Solo noticias de última hora
        self.geolocator = GeoLocator()
        self.notifier = Notifier(config.NOTIFICATION_CONFIG)
        self.storage = NewsStorage(config.PROCESSED_NEWS_FILE)
        
        self.costco_locations = config.COSTCO_LOCATIONS
        self.radius_km = config.RADIUS_KM
        self.use_ai = use_ai
        
        # Inicializar Twitter scraper con autenticación
        self.twitter_scraper = None
        if TWITTER_AUTH_AVAILABLE:
            try:
                self.twitter_scraper = TwitterScraperAuth()
                if self.twitter_scraper.is_configured():
                    print("✓ Twitter scraper configurado con cookies")
                else:
                    print("⚠️  Cookies de Twitter no configuradas")
                    self.twitter_scraper = None
            except Exception as e:
                print(f"⚠️  Error inicializando Twitter scraper: {e}")
                self.twitter_scraper = None
        
        if use_ai:
            print("✓ Sistema inicializado con análisis de IA (OpenAI)")
        else:
            print("✓ Sistema inicializado con análisis tradicional")
        print()
    
    def send_monitoring_summary(self, news_analyzed: int, alerts_sent: int):
        """Envía un resumen del monitoreo realizado."""
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        if alerts_sent > 0:
            # Si se enviaron alertas, el resumen ya está en las alertas individuales
            return
        
        # Enviar resumen cuando NO hay alertas
        summary_data = {
            'timestamp': timestamp,
            'news_analyzed': news_analyzed,
            'alerts_sent': alerts_sent
        }
        
        self.notifier.send_monitoring_summary(summary_data)
    
    def process_news_item_with_ai(self, news_item: dict) -> bool:
        """
        Procesa una noticia individual usando análisis de IA.
        
        Args:
            news_item: Diccionario con información de la noticia
        
        Returns:
            True si se envió una alerta, False en caso contrario
        """
        titulo = news_item.get('titulo', '')
        url = news_item.get('url', '')
        fuente = news_item.get('fuente', '')
        
        # Verificar si ya fue procesada
        if url and self.storage.is_processed(url):
            return False
        
        # Paso 0: Verificar antigüedad de la noticia (máximo 1 hora)
        is_recent, time_reason = self.time_filter.filter_news_item(news_item)
        if not is_recent:
            print(f"   ⏰ {time_reason} - Descartada")
            return False
        
        # Paso 1: Pre-filtrado básico (rápido, sin IA)
        is_high_impact, category = self.analyzer.check_high_impact(titulo)
        
        if not is_high_impact:
            return False
        
        print(f"📰 Candidata detectada: {titulo[:80]}...")
        
        # Paso 2: Obtener contenido completo
        content = titulo
        if url:
            full_content = self.scraper.get_article_content(url)
            if full_content:
                content = full_content
        
        # Paso 3: Análisis completo con IA
        print(f"   🤖 Analizando con IA...")
        ai_result = self.ai_analyzer.analyze_news(titulo, content)
        
        if not ai_result:
            print(f"   ⚠️  Error en análisis IA, usando método tradicional")
            return self.process_news_item_traditional(news_item)
        
        # Verificar relevancia según IA
        if not ai_result.get('is_relevant', False):
            reason = ai_result.get('exclusion_reason', 'No relevante')
            print(f"   ❌ Descartada por IA: {reason}")
            return False
        
        print(f"   ✓ Relevante - Categoría: {ai_result.get('category', 'N/A')}")
        print(f"   ⚡ Severidad: {ai_result.get('severity', 0)}/10")
        
        # Paso 4: Extraer ubicación (priorizar resultado de IA)
        location_info = ai_result.get('location', {})
        location_text = location_info.get('extracted')
        location_confidence = location_info.get('confidence', 0)
        is_specific = location_info.get('is_specific', False)
        
        if not location_text or not is_specific:
            print(f"   ⚠️  Ubicación no específica o no detectada")
            return False
        
        print(f"   📍 Ubicación: {location_text} (confianza: {location_confidence:.2f})")
        
        # Paso 5: Geocodificar ubicación
        normalized_location = location_info.get('normalized', location_text)
        coords = self.geolocator.geocode_location(normalized_location + ", Monterrey, NL")
        
        if not coords:
            # Intentar con ubicación original
            coords = self.geolocator.geocode_location(location_text + ", Monterrey, NL")
        
        if not coords:
            print(f"   ⚠️  No se pudo geocodificar la ubicación")
            return False
        
        print(f"   🗺️  Coordenadas: {coords[0]:.6f}, {coords[1]:.6f}")
        
        # Paso 6: Verificar si está dentro del radio
        is_within, nearest_costco = self.geolocator.is_within_radius(
            coords, self.costco_locations, self.radius_km
        )
        
        # Paso 6.5: Si está fuera del radio, verificar vialidades clave
        if not is_within:
            content_lower = content.lower()
            for costco_name, costco_data in self.costco_locations.items():
                vialidades = costco_data.get('vialidades_clave', [])
                for vialidad in vialidades:
                    if vialidad in content_lower:
                        print(f"   ✓ Vialidad clave: '{vialidad}' ({costco_name})")
                        costco_coords = (costco_data['lat'], costco_data['lon'])
                        distancia = self.geolocator.calculate_distance(coords, costco_coords)
                        nearest_costco = {
                            'nombre': costco_name,
                            'direccion': costco_data['direccion'],
                            'distancia_km': round(distancia, 2)
                        }
                        is_within = True
                        break
                if is_within:
                    break
            
            if not is_within:
                print(f"   ❌ Fuera del radio ({nearest_costco['distancia_km']} km)")
                return False
        
        print(f"   ✓ Dentro del radio: {nearest_costco['distancia_km']} km de {nearest_costco['nombre']}")
        
        # Paso 7: Generar y enviar notificación mejorada
        severity = ai_result.get('severity', 5)
        summary = ai_result.get('summary', titulo)
        details = ai_result.get('details', {})
        
        # Determinar emoji de severidad
        if severity >= 9:
            severity_emoji = "🚨🚨"
        elif severity >= 7:
            severity_emoji = "🚨"
        elif severity >= 5:
            severity_emoji = "⚠️"
        else:
            severity_emoji = "ℹ️"
        
        notification_data = {
            'categoria': self.analyzer.extract_category_label(ai_result.get('category', category)),
            'titulo': titulo,
            'ubicacion': location_text,
            'distancia_km': nearest_costco['distancia_km'],
            'costco_cercano': nearest_costco['nombre'],
            'costco_direccion': nearest_costco['direccion'],
            'fuente': fuente,
            'url': url if url else 'No disponible',
            'resumen': summary,
            'severity': severity,
            'severity_emoji': severity_emoji,
            'victims': details.get('victims', 0),
            'traffic_impact': details.get('traffic_impact', 'unknown'),
            'emergency_services': details.get('emergency_services', False)
        }
        
        self.notifier.notify(notification_data)
        
        # Marcar como procesada
        if url:
            self.storage.mark_as_processed(url)
        
        return True
    
    def process_news_item_traditional(self, news_item: dict) -> bool:
        """
        Procesa una noticia usando el método tradicional (fallback).
        
        Args:
            news_item: Diccionario con información de la noticia
        
        Returns:
            True si se envió una alerta, False en caso contrario
        """
        titulo = news_item.get('titulo', '')
        url = news_item.get('url', '')
        fuente = news_item.get('fuente', '')
        
        # Verificar si ya fue procesada
        if url and self.storage.is_processed(url):
            return False
        
        # Paso 0: Verificar antigüedad de la noticia (máximo 1 hora)
        is_recent, time_reason = self.time_filter.filter_news_item(news_item)
        if not is_recent:
            print(f"   ⏰ {time_reason} - Descartada")
            return False
        
        # Paso 1: Verificar si es de alto impacto
        is_high_impact, category = self.analyzer.check_high_impact(titulo)
        
        if not is_high_impact:
            return False
        
        print(f"📰 Noticia de alto impacto: {titulo[:80]}...")
        print(f"   Categoría: {self.analyzer.extract_category_label(category)}")
        
        # Paso 2: Obtener contenido completo
        content = titulo
        if url:
            full_content = self.scraper.get_article_content(url)
            if full_content:
                content = full_content
        
        # Paso 3: Extraer ubicación
        location_text = self.analyzer.extract_location(content)
        
        if not location_text:
            print(f"   ⚠️  No se pudo extraer ubicación")
            return False
        
        print(f"   📍 Ubicación: {location_text}")
        
        # Paso 4: Geocodificar
        coords = self.geolocator.geocode_location(location_text)
        
        if not coords:
            print(f"   ⚠️  No se pudo geocodificar")
            return False
        
        print(f"   🗺️  Coordenadas: {coords[0]:.6f}, {coords[1]:.6f}")
        
        # Paso 5: Verificar radio
        is_within, nearest_costco = self.geolocator.is_within_radius(
            coords, self.costco_locations, self.radius_km
        )
        
        # Verificar vialidades clave si está fuera del radio
        if not is_within:
            content_lower = content.lower()
            for costco_name, costco_data in self.costco_locations.items():
                vialidades = costco_data.get('vialidades_clave', [])
                for vialidad in vialidades:
                    if vialidad in content_lower:
                        print(f"   ✓ Vialidad clave: '{vialidad}'")
                        costco_coords = (costco_data['lat'], costco_data['lon'])
                        distancia = self.geolocator.calculate_distance(coords, costco_coords)
                        nearest_costco = {
                            'nombre': costco_name,
                            'direccion': costco_data['direccion'],
                            'distancia_km': round(distancia, 2)
                        }
                        is_within = True
                        break
                if is_within:
                    break
            
            if not is_within:
                print(f"   ❌ Fuera del radio ({nearest_costco['distancia_km']} km)")
                return False
        
        print(f"   ✓ Dentro del radio: {nearest_costco['distancia_km']} km")
        
        # Paso 6: Notificar
        notification_data = {
            'categoria': self.analyzer.extract_category_label(category),
            'titulo': titulo,
            'ubicacion': location_text,
            'distancia_km': nearest_costco['distancia_km'],
            'costco_cercano': nearest_costco['nombre'],
            'costco_direccion': nearest_costco['direccion'],
            'fuente': fuente,
            'url': url if url else 'No disponible',
            'resumen': content[:300] + '...' if len(content) > 300 else content
        }
        
        self.notifier.notify(notification_data)
        
        if url:
            self.storage.mark_as_processed(url)
        
        return True
    
    def monitor_sources(self):
        """Monitorea todas las fuentes de noticias configuradas."""
        print(f"\n{'='*70}")
        print(f"🔍 Iniciando monitoreo - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        if self.use_ai:
            print(f"🤖 Modo: Análisis con IA (OpenAI)")
        else:
            print(f"📊 Modo: Análisis tradicional")
        print(f"⏰ Ventana de tiempo: {self.time_filter.get_time_window_description()}")
        print(f"{'='*70}\n")
        
        news_found = 0
        alerts_sent = 0
        
        # Monitorear portales de noticias
        for source in config.NEWS_SOURCES:
            print(f"Monitoreando: {source['nombre']}...")
            
            try:
                if source.get('tipo') == 'milenio':
                    news_items = self.scraper.scrape_milenio(source['url'])
                else:
                    news_items = self.scraper.scrape_generic(source['url'], source['nombre'])
                
                print(f"  → {len(news_items)} noticias encontradas")
                news_found += len(news_items)
                
                for item in news_items:
                    if self.use_ai:
                        result = self.process_news_item_with_ai(item)
                    else:
                        result = self.process_news_item_traditional(item)
                    
                    if result:
                        alerts_sent += 1
                
                time.sleep(2)
                
            except Exception as e:
                print(f"  ⚠️  Error monitoreando {source['nombre']}: {e}")
        
        # Monitorear Twitter
        print("\nMonitoreando Twitter/X...")
        if self.twitter_scraper:
            print("🔐 Usando autenticación con cookies (twscrape)")
            for twitter_account in config.TWITTER_ACCOUNTS:
                try:
                    handle = twitter_account['handle']
                    print(f"Monitoreando: @{handle}...")
                    
                    # Usar TwitterScraperAuth directamente
                    tweets = self.twitter_scraper.get_user_tweets(handle, count=10)
                    
                    if tweets:
                        print(f"  ✓ {len(tweets)} tweets extraídos de @{handle}")
                        news_found += len(tweets)
                        
                        for tweet in tweets:
                            if self.use_ai:
                                result = self.process_news_item_with_ai(tweet)
                            else:
                                result = self.process_news_item_traditional(tweet)
                            
                            if result:
                                alerts_sent += 1
                    else:
                        print(f"  → 0 tweets encontrados")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    print(f"  ⚠️  Error monitoreando @{handle}: {e}")
                    import traceback
                    traceback.print_exc()
        else:
            print("⚠️  Twitter scraper no disponible (cookies no configuradas)")
            print("  Saltando monitoreo de Twitter...")
            for twitter_account in config.TWITTER_ACCOUNTS:
                print(f"Monitoreando: @{twitter_account['handle']}...")
                print(f"  → 0 tweets encontrados (sin autenticación)")
        
        print(f"\n{'='*70}")
        print(f"✓ Monitoreo completado - {news_found} noticias analizadas")
        print(f"✓ Alertas enviadas: {alerts_sent}")
        print(f"{'='*70}\n")
        
        # Enviar resumen
        self.send_monitoring_summary(news_found, alerts_sent)
    
    def run_once(self):
        """Ejecuta un ciclo de monitoreo."""
        try:
            self.monitor_sources()
        except Exception as e:
            print(f"Error en el monitoreo: {e}")
    
    def run_continuous(self, interval_minutes: int = 30):
        """
        Ejecuta el monitoreo de forma continua.
        
        Args:
            interval_minutes: Intervalo entre ejecuciones en minutos
        """
        print(f"Modo continuo activado - Intervalo: {interval_minutes} minutos")
        print("Presiona Ctrl+C para detener\n")
        
        try:
            while True:
                self.run_once()
                print(f"⏳ Esperando {interval_minutes} minutos hasta el próximo monitoreo...")
                time.sleep(interval_minutes * 60)
        except KeyboardInterrupt:
            print("\n\n🛑 Monitoreo detenido por el usuario")


def main():
    """Función principal."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   Sistema de Monitoreo de Noticias de Alto Impacto               ║
║   Monterrey, Nuevo León - Versión con IA                         ║
║   Powered by OpenAI                                              ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Inicializar con análisis de IA
    monitor = NewsMonitorAI(use_ai=True)
    
    # Ejecutar una sola vez
    monitor.run_once()
    
    # Para ejecución continua, descomentar:
    # monitor.run_continuous(interval_minutes=30)


if __name__ == "__main__":
    main()
