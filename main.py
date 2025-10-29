"""
Script principal del sistema de monitoreo de noticias de alto impacto.
"""

import time
from datetime import datetime

# Importar módulos locales
import config
from scraper import NewsScraperV2 as NewsScraper
from analyzer import NewsAnalyzer
from geolocation import GeoLocator
from notifier import Notifier
from storage import NewsStorage


class NewsMonitor:
    """Clase principal que orquesta el monitoreo de noticias."""
    
    def __init__(self):
        """Inicializa todos los componentes del sistema."""
        print("Inicializando sistema de monitoreo de noticias...")
        
        self.scraper = NewsScraper()
        self.analyzer = NewsAnalyzer(config.KEYWORDS)
        self.geolocator = GeoLocator()
        self.notifier = Notifier(config.NOTIFICATION_CONFIG)
        self.storage = NewsStorage(config.PROCESSED_NEWS_FILE)
        
        self.costco_locations = config.COSTCO_LOCATIONS
        self.radius_km = config.RADIUS_KM
        
        print("✓ Sistema inicializado correctamente\n")
    
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
    
    def process_news_item(self, news_item: dict) -> bool:
        """
        Procesa una noticia individual.
        
        Args:
            news_item: Diccionario con información de la noticia
        """
        titulo = news_item.get('titulo', '')
        url = news_item.get('url', '')
        fuente = news_item.get('fuente', '')
        
        # Verificar si ya fue procesada
        if url and self.storage.is_processed(url):
            return
        
        # Paso 1: Verificar si es de alto impacto
        is_high_impact, category = self.analyzer.check_high_impact(titulo)
        
        if not is_high_impact:
            return False
        
        print(f"📰 Noticia de alto impacto detectada: {titulo[:80]}...")
        print(f"   Categoría: {self.analyzer.extract_category_label(category)}")
        
        # Paso 2: Obtener contenido completo
        content = titulo  # Por defecto usar el titular
        if url:
            full_content = self.scraper.get_article_content(url)
            if full_content:
                content = full_content
        
        # Paso 3: Extraer ubicación
        location_text = self.analyzer.extract_location(content)
        
        if not location_text:
            print(f"   ⚠️  No se pudo extraer ubicación de la noticia")
            return False
        
        print(f"   📍 Ubicación detectada: {location_text}")
        
        # Paso 4: Geocodificar ubicación
        coords = self.geolocator.geocode_location(location_text)
        
        if not coords:
            print(f"   ⚠️  No se pudo geocodificar la ubicación")
            return False
        
        print(f"   🗺️  Coordenadas: {coords[0]:.6f}, {coords[1]:.6f}")
        
        # Paso 5: Verificar si está dentro del radio
        is_within, nearest_costco = self.geolocator.is_within_radius(
            coords, self.costco_locations, self.radius_km
        )
        
        # Paso 5.5: Si está fuera del radio, verificar vialidades clave
        if not is_within:
            # Verificar si menciona alguna vialidad clave de algún Costco
            content_lower = content.lower()
            for costco_name, costco_data in self.costco_locations.items():
                vialidades = costco_data.get('vialidades_clave', [])
                for vialidad in vialidades:
                    if vialidad in content_lower:
                        print(f"   ✓ Vialidad clave detectada: '{vialidad}' (relacionada con {costco_name})")
                        # Recalcular distancia a este Costco específico
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
                print(f"   ❌ Fuera del radio ({nearest_costco['distancia_km']} km) y sin vialidades clave")
                return False
        
        print(f"   ✓ Dentro del radio: {nearest_costco['distancia_km']} km de {nearest_costco['nombre']}")
        
        # Paso 6: Generar y enviar notificación
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
        
        # Marcar como procesada
        if url:
            self.storage.mark_as_processed(url)
        
        return True  # Retornar True si se envió una alerta
    
    def monitor_sources(self):
        """Monitorea todas las fuentes de noticias configuradas."""
        print(f"\n{'='*70}")
        print(f"🔍 Iniciando monitoreo - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
                    result = self.process_news_item(item)
                    if result:
                        alerts_sent += 1
                
                time.sleep(2)  # Pausa entre fuentes para no sobrecargar
                
            except Exception as e:
                print(f"  ⚠️  Error monitoreando {source['nombre']}: {e}")
        
        # Monitorear Twitter usando Nitter
        print("\nMonitoreando Twitter/X...")
        for twitter_account in config.TWITTER_ACCOUNTS:
            try:
                print(f"Monitoreando: @{twitter_account['handle']}...")
                tweets = self.scraper.scrape_twitter_profile(
                    twitter_account['url'],
                    twitter_account['handle']
                )
                
                if tweets:
                    print(f"  → {len(tweets)} tweets encontrados")
                    news_found += len(tweets)
                    
                    for tweet in tweets:
                        result = self.process_news_item(tweet)
                        if result:
                            alerts_sent += 1
                else:
                    print(f"  → 0 tweets encontrados")
                
                time.sleep(2)  # Pausa entre cuentas
                
            except Exception as e:
                print(f"  ⚠️  Error monitoreando @{twitter_account['handle']}: {e}")
        
        print(f"\n{'='*70}")
        print(f"✓ Monitoreo completado - {news_found} noticias analizadas")
        print(f"✓ Alertas enviadas: {alerts_sent}")
        print(f"{'='*70}\n")
        
        # Enviar resumen del monitoreo
        self.send_monitoring_summary(news_found, alerts_sent)
    
    def run_once(self):
        """Ejecuta un ciclo de monitoreo."""
        try:
            self.monitor_sources()
        except Exception as e:
            print(f"Error en el monitoreo: {e}")
    
    def run_continuous(self, interval_minutes: int = 15):
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
║   Monterrey, Nuevo León - Radio 5 km Costco                      ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    monitor = NewsMonitor()
    
    # Ejecutar una sola vez
    monitor.run_once()
    
    # Para ejecución continua, descomentar la siguiente línea:
    # monitor.run_continuous(interval_minutes=15)


if __name__ == "__main__":
    main()

