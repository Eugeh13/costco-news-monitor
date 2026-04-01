"""
Módulo de scraping v3 - Multi-source confiable con IA.

Fuentes:
1. Google News RSS - Feeds personalizados por query (gratis, no requiere API key)
2. GNews Python - Búsqueda + artículo completo (gratis, no requiere API key)  
3. RSS directo - Feeds de medios locales (Milenio, Info7, etc.)
4. Crawl4AI - Extracción inteligente de artículos completos (open-source)

Elimina la dependencia de selectores CSS frágiles.
"""

import asyncio
import hashlib
import re
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
import xml.etree.ElementTree as ET

import requests
import feedparser

# GNews - búsqueda de Google News con artículos completos
try:
    from gnews import GNews
    GNEWS_AVAILABLE = True
except ImportError:
    GNEWS_AVAILABLE = False
    print("⚠️ gnews no instalado. pip install gnews")

# Crawl4AI - scraping inteligente para artículos completos
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    print("⚠️ crawl4ai no instalado. pip install crawl4ai")


# ============================================================
# Modelo de datos
# ============================================================

@dataclass
class NewsItem:
    """Estructura estandarizada para una noticia de cualquier fuente."""
    titulo: str
    contenido: str
    url: str
    fuente: str
    fecha_pub: Optional[datetime] = None
    source_type: str = ""  # "google_rss", "gnews", "rss_directo", "crawl4ai"
    content_hash: str = ""
    full_article: Optional[str] = None  # Contenido completo (lazy load)
    
    def __post_init__(self):
        if not self.content_hash:
            text = f"{self.titulo}{self.url}".encode()
            self.content_hash = hashlib.md5(text).hexdigest()
    
    def to_dict(self) -> dict:
        """Convierte a diccionario compatible con el sistema actual."""
        return {
            'titulo': self.titulo,
            'contenido': self.contenido,
            'url': self.url,
            'fuente': self.fuente,
            'fecha_pub': self.fecha_pub.isoformat() if self.fecha_pub else None,
            'source_type': self.source_type,
            'content_hash': self.content_hash,
        }


# ============================================================
# Fuente 1: Google News RSS (gratuito, confiable, no API key)
# ============================================================

class GoogleNewsRSS:
    """
    Obtiene noticias de Google News vía RSS feeds personalizados.
    
    Formato: https://news.google.com/rss/search?q=QUERY&hl=es-419&gl=MX&ceid=MX:es-419
    
    Ventajas:
    - Gratis, sin API key
    - Agrega múltiples fuentes automáticamente
    - Respeta el formato RSS estándar
    - Resultados frescos (últimas horas)
    """
    
    BASE_URL = "https://news.google.com/rss/search"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; NewsMonitor/3.0)'
        })
    
    def _build_query(self, terms: List[str], location: str = "Monterrey") -> str:
        """
        Construye query optimizado para Google News.
        
        Usa operadores de búsqueda avanzados:
        - Comillas para frases exactas
        - OR para alternativas
        - Ubicación como contexto
        """
        # Agrupar términos con OR
        query_parts = []
        for term in terms:
            if ' ' in term:
                query_parts.append(f'"{term}"')
            else:
                query_parts.append(term)
        
        query = f"({' OR '.join(query_parts)}) {location}"
        return query
    
    def fetch_feed(self, query: str, max_results: int = 30) -> List[NewsItem]:
        """Descarga y parsea un feed RSS de Google News."""
        params = {
            'q': query,
            'hl': 'es-419',
            'gl': 'MX',
            'ceid': 'MX:es-419',
        }
        
        try:
            url = f"{self.BASE_URL}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            items = []
            
            for entry in feed.entries[:max_results]:
                # Parsear fecha
                fecha = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    fecha = datetime(*entry.published_parsed[:6])
                
                # Extraer fuente real del título (Google News agrega " - Fuente")
                titulo = entry.get('title', '')
                fuente_real = "Google News"
                if ' - ' in titulo:
                    parts = titulo.rsplit(' - ', 1)
                    titulo = parts[0].strip()
                    fuente_real = parts[1].strip()
                
                # Descripción (snippet)
                descripcion = entry.get('summary', titulo)
                # Limpiar HTML del summary
                descripcion = re.sub(r'<[^>]+>', '', descripcion).strip()
                
                # URL real (Google News redirige)
                link = entry.get('link', '')
                
                items.append(NewsItem(
                    titulo=titulo,
                    contenido=descripcion,
                    url=link,
                    fuente=fuente_real,
                    fecha_pub=fecha,
                    source_type="google_rss"
                ))
            
            return items
            
        except Exception as e:
            print(f"  ⚠️ Error en Google News RSS: {e}")
            return []
    
    def search_monterrey_incidents(self) -> List[NewsItem]:
        """
        Ejecuta múltiples queries optimizados para incidentes en Monterrey.
        
        Estrategia: queries específicos por tipo de evento para maximizar cobertura.
        """
        all_items = []
        seen_hashes = set()
        
        queries = [
            # Accidentes viales
            self._build_query(
                ["accidente", "choque", "volcadura", "atropello", "colisión"],
                "Monterrey Nuevo León"
            ),
            # Incendios
            self._build_query(
                ["incendio", "fuego", "explosión", "conflagración"],
                "Monterrey Nuevo León"
            ),
            # Seguridad
            self._build_query(
                ["balacera", "tiroteo", "enfrentamiento", "detonaciones", "persecución"],
                "Monterrey Nuevo León"
            ),
            # Bloqueos y vialidad
            self._build_query(
                ["bloqueo", "cierre vial", "manifestación", "protesta"],
                "Monterrey Nuevo León"
            ),
            # Desastres naturales
            self._build_query(
                ["inundación", "tromba", "desbordamiento"],
                "Monterrey Nuevo León"
            ),
            # Query general de última hora
            self._build_query(
                ["emergencia", "alerta", "accidente"],
                "área metropolitana Monterrey"
            ),
        ]
        
        for query in queries:
            items = self.fetch_feed(query, max_results=15)
            for item in items:
                if item.content_hash not in seen_hashes:
                    seen_hashes.add(item.content_hash)
                    all_items.append(item)
            time.sleep(0.5)  # Rate limiting cortés
        
        print(f"  → Google News RSS: {len(all_items)} noticias únicas")
        return all_items


# ============================================================
# Fuente 2: GNews Python (búsqueda + artículo completo)
# ============================================================

class GNewsSource:
    """
    Usa la librería gnews para buscar en Google News y obtener artículos completos.
    
    Ventajas:
    - Obtiene el artículo completo (no solo el snippet)
    - Filtro por idioma, país y periodo
    - Sin API key
    """
    
    def __init__(self):
        if not GNEWS_AVAILABLE:
            self.client = None
            return
        
        self.client = GNews(
            language='es',
            country='MX',
            period='1h',  # Solo última hora
            max_results=20,
            exclude_websites=[
                'youtube.com',
                'tiktok.com',
                'facebook.com',
            ]
        )
    
    def search(self, query: str) -> List[NewsItem]:
        """Busca noticias con GNews."""
        if not self.client:
            return []
        
        try:
            results = self.client.get_news(query)
            items = []
            
            for article in results:
                fecha = None
                if article.get('published date'):
                    try:
                        fecha = datetime.strptime(
                            article['published date'], 
                            '%a, %d %b %Y %H:%M:%S %Z'
                        )
                    except (ValueError, TypeError):
                        pass
                
                items.append(NewsItem(
                    titulo=article.get('title', ''),
                    contenido=article.get('description', ''),
                    url=article.get('url', ''),
                    fuente=article.get('publisher', {}).get('title', 'GNews'),
                    fecha_pub=fecha,
                    source_type="gnews"
                ))
            
            return items
            
        except Exception as e:
            print(f"  ⚠️ Error en GNews: {e}")
            return []
    
    def get_full_article(self, url: str) -> Optional[str]:
        """Obtiene el artículo completo usando newspaper3k directamente."""
        if not url:
            return None
        
        # Intentar con newspaper3k directamente (más confiable que gnews.get_full_article)
        try:
            import newspaper
            article = newspaper.Article(url, language='es')
            article.download()
            article.parse()
            if article.text and len(article.text) > 100:
                return article.text[:3000]
        except Exception as e:
            print(f"  ⚠️ Error newspaper3k: {e}")
        
        # Fallback: intentar con gnews
        if self.client:
            try:
                article = self.client.get_full_article(url)
                if article:
                    return article.text
            except Exception as e:
                print(f"  ⚠️ Error gnews.get_full_article: {e}")
        
        return None
    
    def search_monterrey_incidents(self) -> List[NewsItem]:
        """Ejecuta búsquedas de incidentes en Monterrey."""
        if not self.client:
            print("  ⚠️ GNews no disponible")
            return []
        
        all_items = []
        seen_hashes = set()
        
        search_terms = [
            "accidente Monterrey",
            "incendio Monterrey Nuevo León",
            "balacera Monterrey",
            "choque Monterrey",
            "bloqueo vial Monterrey",
            "emergencia Monterrey hoy",
        ]
        
        for term in search_terms:
            items = self.search(term)
            for item in items:
                if item.content_hash not in seen_hashes:
                    seen_hashes.add(item.content_hash)
                    all_items.append(item)
            time.sleep(1)  # Rate limiting
        
        print(f"  → GNews: {len(all_items)} noticias únicas")
        return all_items


# ============================================================
# Fuente 3: RSS directo de medios locales
# ============================================================

class DirectRSSSource:
    """
    Parsea feeds RSS directos de medios locales de Monterrey/NL.
    
    Ventajas:
    - Fuentes locales que Google News puede no indexar inmediatamente
    - Noticias hiperlocales
    - Muy confiable (RSS estándar)
    """
    
    # Feeds RSS de medios locales de Monterrey/NL
    DEFAULT_FEEDS = [
        {
            'url': 'https://www.milenio.com/rss',
            'nombre': 'Milenio',
            'filtro_geo': True,  # Necesita filtrar por ubicación
        },
        {
            'url': 'https://vanguardia.com.mx/rss.xml',
            'nombre': 'Vanguardia',
            'filtro_geo': True,
        },
    ]
    
    def __init__(self, feeds: Optional[List[dict]] = None):
        self.feeds = feeds or self.DEFAULT_FEEDS
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; NewsMonitor/3.0)'
        })
    
    def fetch_feed(self, feed_config: dict) -> List[NewsItem]:
        """Descarga y parsea un feed RSS individual."""
        url = feed_config['url']
        nombre = feed_config['nombre']
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            feed = feedparser.parse(response.content)
            items = []
            
            for entry in feed.entries[:30]:
                fecha = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    fecha = datetime(*entry.published_parsed[:6])
                
                titulo = entry.get('title', '').strip()
                descripcion = entry.get('summary', entry.get('description', titulo))
                descripcion = re.sub(r'<[^>]+>', '', descripcion).strip()
                link = entry.get('link', '')
                
                if len(titulo) < 15:
                    continue
                
                items.append(NewsItem(
                    titulo=titulo,
                    contenido=descripcion,
                    url=link,
                    fuente=nombre,
                    fecha_pub=fecha,
                    source_type="rss_directo"
                ))
            
            return items
            
        except Exception as e:
            print(f"  ⚠️ Error en RSS {nombre}: {e}")
            return []
    
    def fetch_all(self) -> List[NewsItem]:
        """Descarga todos los feeds configurados."""
        all_items = []
        seen_hashes = set()
        
        for feed_config in self.feeds:
            items = self.fetch_feed(feed_config)
            for item in items:
                if item.content_hash not in seen_hashes:
                    seen_hashes.add(item.content_hash)
                    all_items.append(item)
        
        print(f"  → RSS directo: {len(all_items)} noticias únicas")
        return all_items


# ============================================================
# Extracción profunda: Crawl4AI o fallback requests
# ============================================================

class DeepArticleReader:
    """
    Extrae el contenido completo de un artículo.
    
    Prioridad:
    1. Crawl4AI (convierte a Markdown limpio, entiende la estructura)
    2. GNews full article (si está disponible)
    3. Requests + heurísticas (fallback)
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                         'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36'
        })
        self._gnews = GNewsSource() if GNEWS_AVAILABLE else None
    
    async def read_with_crawl4ai(self, url: str) -> Optional[str]:
        """Extrae artículo completo con Crawl4AI."""
        if not CRAWL4AI_AVAILABLE:
            return None
        
        try:
            async with AsyncWebCrawler() as crawler:
                result = await crawler.arun(url=url)
                if result and result.markdown:
                    # Crawl4AI devuelve Markdown limpio
                    content = result.markdown
                    # Limitar a contenido relevante (primeros 3000 chars)
                    if len(content) > 3000:
                        content = content[:3000]
                    return content
        except Exception as e:
            print(f"  ⚠️ Crawl4AI error: {e}")
        
        return None
    
    def read_with_gnews(self, url: str) -> Optional[str]:
        """Extrae artículo con GNews."""
        if self._gnews:
            return self._gnews.get_full_article(url)
        return None
    
    def read_with_requests(self, url: str) -> Optional[str]:
        """Fallback: extrae con requests + heurísticas."""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Eliminar scripts, styles, nav, footer
            for tag in soup.find_all(['script', 'style', 'nav', 'footer', 'aside', 'header']):
                tag.decompose()
            
            # Buscar contenido principal
            selectors = [
                'article',
                '[class*="article-content"]',
                '[class*="entry-content"]',
                '[class*="post-content"]',
                '[class*="story-body"]',
                '[class*="nota"]',
                'main',
            ]
            
            content = None
            for selector in selectors:
                elem = soup.select_one(selector)
                if elem:
                    content = elem.get_text(separator=' ', strip=True)
                    break
            
            if not content:
                paragraphs = soup.find_all('p')
                content = ' '.join(
                    p.get_text(strip=True) for p in paragraphs 
                    if len(p.get_text(strip=True)) > 40
                )
            
            return content[:3000] if content else None
            
        except Exception as e:
            print(f"  ⚠️ Error en lectura fallback: {e}")
            return None
    
    async def read_article(self, url: str) -> Optional[str]:
        """
        Lee un artículo completo con la mejor herramienta disponible.
        
        Intenta en orden: Crawl4AI → GNews → requests fallback
        """
        if not url:
            return None
        
        # 1. Crawl4AI (mejor calidad)
        content = await self.read_with_crawl4ai(url)
        if content and len(content) > 100:
            return content
        
        # 2. GNews full article
        content = self.read_with_gnews(url)
        if content and len(content) > 100:
            return content
        
        # 3. Fallback requests
        content = self.read_with_requests(url)
        return content
    
    def read_article_sync(self, url: str) -> Optional[str]:
        """Versión síncrona de read_article."""
        try:
            return asyncio.get_event_loop().run_until_complete(self.read_article(url))
        except RuntimeError:
            # No hay event loop, crear uno nuevo
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self.read_article(url))
            finally:
                loop.close()


# ============================================================
# Orquestador principal
# ============================================================

class NewsScraperV3:
    """
    Scraper multi-fuente que reemplaza el scraper v2 basado en BeautifulSoup.
    
    Arquitectura:
    1. Recolecta noticias de múltiples fuentes confiables (RSS, Google News)
    2. Deduplica por hash de contenido
    3. Proporciona lectura profunda bajo demanda (Crawl4AI/GNews)
    
    Compatible con la interfaz existente (to_dict() en NewsItem).
    """
    
    def __init__(self):
        self.google_rss = GoogleNewsRSS()
        self.gnews_source = GNewsSource()
        self.rss_direct = DirectRSSSource()
        self.deep_reader = DeepArticleReader()
        
        print("✓ Scraper v3 inicializado:")
        print(f"  - Google News RSS: ✓")
        print(f"  - GNews: {'✓' if GNEWS_AVAILABLE else '✗ (pip install gnews)'}")
        print(f"  - RSS directo: {len(self.rss_direct.feeds)} feeds")
        print(f"  - Crawl4AI: {'✓' if CRAWL4AI_AVAILABLE else '✗ (pip install crawl4ai)'}")
    
    def collect_all_news(self) -> List[NewsItem]:
        """
        Recolecta noticias de TODAS las fuentes configuradas.
        Deduplica automáticamente.
        
        Returns:
            Lista de NewsItem únicos, ordenados por fecha (más recientes primero).
        """
        all_items = []
        seen_hashes = set()
        
        def add_unique(items: List[NewsItem]):
            for item in items:
                if item.content_hash not in seen_hashes:
                    seen_hashes.add(item.content_hash)
                    all_items.append(item)
        
        # 1. Google News RSS (más cobertura)
        print("\n📡 Fuente 1: Google News RSS...")
        try:
            add_unique(self.google_rss.search_monterrey_incidents())
        except Exception as e:
            print(f"  ⚠️ Error Google RSS: {e}")
        
        # 2. GNews (artículos completos disponibles)
        print("📡 Fuente 2: GNews...")
        try:
            add_unique(self.gnews_source.search_monterrey_incidents())
        except Exception as e:
            print(f"  ⚠️ Error GNews: {e}")
        
        # 3. RSS directo de medios locales
        print("📡 Fuente 3: RSS directo...")
        try:
            add_unique(self.rss_direct.fetch_all())
        except Exception as e:
            print(f"  ⚠️ Error RSS directo: {e}")
        
        # Ordenar por fecha (más recientes primero)
        all_items.sort(
            key=lambda x: x.fecha_pub or datetime.min,
            reverse=True
        )
        
        print(f"\n📊 Total recolectado: {len(all_items)} noticias únicas de {len(seen_hashes)} fuentes")
        return all_items
    
    def get_article_content(self, url: str) -> Optional[str]:
        """
        Obtiene contenido completo de un artículo.
        Compatible con la interfaz del scraper v2.
        """
        return self.deep_reader.read_article_sync(url)
    
    # ========================================================
    # Métodos de compatibilidad con el sistema actual
    # ========================================================
    
    def scrape_milenio(self, url: str) -> List[Dict]:
        """Compatibilidad: reemplaza scraping de Milenio con RSS."""
        items = self.rss_direct.fetch_feed({
            'url': 'https://www.milenio.com/rss',
            'nombre': 'Milenio'
        })
        return [item.to_dict() for item in items]
    
    def scrape_generic(self, url: str, source_name: str) -> List[Dict]:
        """Compatibilidad: reemplaza scraping genérico con Google News."""
        query = f"site:{url.split('/')[2]} Monterrey"
        items = self.google_rss.fetch_feed(query, max_results=20)
        return [item.to_dict() for item in items]
    
    def scrape_twitter_profile(self, url: str, handle: str) -> List[Dict]:
        """Compatibilidad: Twitter ya no es confiable, usar Google News."""
        query = f"@{handle} Monterrey"
        items = self.google_rss.fetch_feed(query, max_results=10)
        return [item.to_dict() for item in items]


# ============================================================
# Función de utilidad para pruebas
# ============================================================

def test_scraper():
    """Prueba el scraper v3."""
    print("""
╔════════════════════════════════════════╗
║  Test: Scraper v3 Multi-Source        ║
╚════════════════════════════════════════╝
""")
    
    scraper = NewsScraperV3()
    
    # Recolectar noticias
    news = scraper.collect_all_news()
    
    print(f"\n{'='*60}")
    print(f"Resultados: {len(news)} noticias")
    print(f"{'='*60}\n")
    
    for i, item in enumerate(news[:10], 1):
        print(f"{i}. [{item.source_type}] {item.fuente}")
        print(f"   {item.titulo[:80]}...")
        if item.fecha_pub:
            print(f"   📅 {item.fecha_pub.strftime('%d/%m/%Y %H:%M')}")
        print(f"   🔗 {item.url[:60]}...")
        print()
    
    # Probar lectura profunda del primer artículo
    if news and news[0].url:
        print(f"\n{'='*60}")
        print(f"Probando lectura profunda...")
        print(f"{'='*60}\n")
        
        content = scraper.get_article_content(news[0].url)
        if content:
            print(f"✓ Contenido extraído ({len(content)} chars):")
            print(f"  {content[:200]}...")
        else:
            print("✗ No se pudo extraer contenido")


if __name__ == "__main__":
    test_scraper()
