"""
Módulo de scraping de noticias de portales web.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import time


class NewsScraper:
    """Clase para obtener noticias de portales web."""
    
    def __init__(self):
        """Inicializa el scraper con headers para simular un navegador."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def fetch_page(self, url: str) -> Optional[str]:
        """
        Descarga el contenido HTML de una página.
        
        Args:
            url: URL de la página
        
        Returns:
            Contenido HTML o None si hay error
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error descargando {url}: {e}")
            return None
    
    def scrape_milenio(self, url: str) -> List[Dict]:
        """
        Extrae noticias del portal Milenio.
        
        Args:
            url: URL del portal
        
        Returns:
            Lista de diccionarios con noticias
        """
        html = self.fetch_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # Determinar nombre de fuente
        fuente_nombre = "Milenio Última Hora" if "ultima-hora" in url else "Milenio Monterrey"
        
        # Buscar artículos - Milenio usa diferentes estructuras
        # 1. Intentar buscar por article tags
        articles = soup.find_all('article', limit=30)
        
        # 2. Si no hay articles, buscar divs con clases de noticias
        if not articles:
            articles = soup.find_all('div', class_=lambda x: x and ('card' in x.lower() or 'item' in x.lower() or 'post' in x.lower()), limit=30)
        
        # 3. Si aún no hay, buscar por h2/h3 directamente
        if not articles:
            # Crear "artículos" artificiales a partir de headers
            headers = soup.find_all(['h2', 'h3'], limit=30)
            articles = [h.parent if h.parent else h for h in headers]
        
        for article in articles:
            try:
                # Extraer titular
                title_elem = article.find(['h2', 'h3', 'h4', 'h1'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Filtrar títulos muy cortos o irrelevantes
                if len(title) < 15 or title in ['EDICIÓN IMPRESA', 'Impreso']:
                    continue
                
                # Extraer enlace
                link_elem = article.find('a', href=True)
                link = link_elem['href'] if link_elem else None
                
                if link and not link.startswith('http'):
                    link = f"https://www.milenio.com{link}"
                
                # Extraer descripción/resumen si existe
                desc_elem = article.find(['p', 'div'], class_=lambda x: x and ('description' in x.lower() or 'summary' in x.lower() or 'excerpt' in x.lower()))
                descripcion = desc_elem.get_text(strip=True) if desc_elem else title
                
                news_items.append({
                    'titulo': title,
                    'contenido': descripcion,
                    'url': link,
                    'fuente': fuente_nombre
                })
            except Exception as e:
                continue
        
        return news_items
    
    def scrape_generic(self, url: str, source_name: str) -> List[Dict]:
        """
        Scraper genérico para portales de noticias.
        
        Args:
            url: URL del portal
            source_name: Nombre de la fuente
        
        Returns:
            Lista de diccionarios con noticias
        """
        html = self.fetch_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # Buscar elementos comunes de noticias
        # Intentar varios selectores comunes
        selectors = ['article', 'div.noticia', 'div.nota', 'div.news-item']
        
        for selector in selectors:
            articles = soup.select(selector)[:10]
            if articles:
                break
        
        for article in articles:
            try:
                # Buscar titular
                title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                # Buscar enlace
                link_elem = article.find('a', href=True)
                link = link_elem['href'] if link_elem else None
                
                if link and not link.startswith('http'):
                    # Intentar construir URL completa
                    base_url = '/'.join(url.split('/')[:3])
                    link = f"{base_url}{link}"
                
                if title:
                    news_items.append({
                        'titulo': title,
                        'url': link,
                        'fuente': source_name
                    })
            except Exception as e:
                continue
        
        return news_items
    
    def scrape_twitter_profile(self, url: str, handle: str) -> List[Dict]:
        """
        Intenta extraer tweets de una página pública de Twitter/X.
        Usa Nitter como alternativa para acceder a tweets públicos.
        
        Args:
            url: URL del perfil de Twitter
            handle: Handle de la cuenta
        
        Returns:
            Lista de diccionarios con tweets
        """
        tweets = []
        
        # Intentar usar instancias públicas de Nitter (frontend alternativo de Twitter)
        nitter_instances = [
            f"https://nitter.net/{handle}",
            f"https://nitter.privacydev.net/{handle}",
            f"https://nitter.poast.org/{handle}"
        ]
        
        for nitter_url in nitter_instances:
            try:
                html = self.fetch_page(nitter_url)
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Buscar tweets en Nitter
                tweet_items = soup.find_all('div', class_='timeline-item', limit=10)
                
                for tweet_item in tweet_items:
                    try:
                        # Extraer texto del tweet
                        tweet_content = tweet_item.find('div', class_='tweet-content')
                        if not tweet_content:
                            continue
                        
                        texto = tweet_content.get_text(strip=True)
                        
                        # Extraer enlace al tweet
                        link_elem = tweet_item.find('a', class_='tweet-link')
                        tweet_link = None
                        if link_elem and link_elem.get('href'):
                            tweet_link = f"https://twitter.com{link_elem['href']}"
                        
                        if texto and len(texto) > 10:
                            tweets.append({
                                'titulo': texto[:100] + '...' if len(texto) > 100 else texto,
                                'contenido': texto,
                                'url': tweet_link,
                                'fuente': f"Twitter @{handle}"
                            })
                    except Exception as e:
                        continue
                
                # Si encontramos tweets, salir del loop
                if tweets:
                    print(f"  ✓ {len(tweets)} tweets extraídos de @{handle}")
                    return tweets
                    
            except Exception as e:
                continue
        
        # Si no se pudo acceder a Nitter
        if not tweets:
            print(f"  ⚠️  No se pudieron obtener tweets de @{handle} (Nitter no disponible)")
        
        return tweets
    
    def get_article_content(self, url: str) -> Optional[str]:
        """
        Obtiene el contenido completo de un artículo.
        
        Args:
            url: URL del artículo
        
        Returns:
            Texto del artículo o None
        """
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Intentar encontrar el contenido principal
        content_selectors = [
            'article',
            'div.article-body',
            'div.content',
            'div.nota-contenido',
            'div.entry-content'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                # Extraer texto de párrafos
                paragraphs = content.find_all('p')
                text = ' '.join([p.get_text(strip=True) for p in paragraphs])
                return text
        
        # Si no se encuentra, intentar obtener todos los párrafos
        paragraphs = soup.find_all('p')
        if paragraphs:
            text = ' '.join([p.get_text(strip=True) for p in paragraphs[:10]])
            return text
        
        return None

