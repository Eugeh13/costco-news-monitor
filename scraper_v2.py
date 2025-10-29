"""
Módulo de scraping mejorado de noticias - Versión 2
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re


class NewsScraperV2:
    """Clase mejorada para obtener noticias de portales web."""
    
    def __init__(self):
        """Inicializa el scraper con headers para simular un navegador."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Descarga el contenido HTML de una página."""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error descargando {url}: {e}")
            return None
    
    def scrape_milenio_ultima_hora(self, url: str) -> List[Dict]:
        """
        Extrae noticias de Milenio Última Hora usando múltiples estrategias.
        """
        html = self.fetch_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        seen_titles = set()
        
        # Estrategia 1: Buscar todos los enlaces con h2/h3
        for header in soup.find_all(['h2', 'h3'], limit=50):
            link = header.find('a')
            if not link:
                link = header.find_parent('a')
            
            if link and link.get('href'):
                title = header.get_text(strip=True)
                href = link['href']
                
                # Filtrar títulos cortos o duplicados
                if len(title) < 15 or title in seen_titles:
                    continue
                
                seen_titles.add(title)
                
                # Construir URL completa
                if not href.startswith('http'):
                    href = f"https://www.milenio.com{href}"
                
                # Buscar descripción cercana
                desc_elem = header.find_next('p')
                descripcion = desc_elem.get_text(strip=True) if desc_elem else title
                
                news_items.append({
                    'titulo': title,
                    'contenido': descripcion,
                    'url': href,
                    'fuente': 'Milenio Última Hora'
                })
        
        # Estrategia 2: Si no encontramos suficientes, buscar en divs
        if len(news_items) < 5:
            for div in soup.find_all('div', class_=lambda x: x and 'card' in str(x).lower()):
                title_elem = div.find(['h2', 'h3', 'h4'])
                link_elem = div.find('a', href=True)
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    
                    if len(title) >= 15 and title not in seen_titles:
                        seen_titles.add(title)
                        href = link_elem['href']
                        
                        if not href.startswith('http'):
                            href = f"https://www.milenio.com{href}"
                        
                        news_items.append({
                            'titulo': title,
                            'contenido': title,
                            'url': href,
                            'fuente': 'Milenio Última Hora'
                        })
        
        return news_items[:30]  # Limitar a 30 noticias
    
    def scrape_milenio_monterrey(self, url: str) -> List[Dict]:
        """Extrae noticias de Milenio Monterrey."""
        html = self.fetch_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        seen_titles = set()
        
        # Buscar artículos
        articles = soup.find_all('article', limit=30)
        
        for article in articles:
            try:
                title_elem = article.find(['h2', 'h3', 'h4', 'h1'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                if len(title) < 15 or title in seen_titles or title in ['EDICIÓN IMPRESA', 'Impreso']:
                    continue
                
                seen_titles.add(title)
                
                link_elem = article.find('a', href=True)
                link = link_elem['href'] if link_elem else None
                
                if link and not link.startswith('http'):
                    link = f"https://www.milenio.com{link}"
                
                desc_elem = article.find('p')
                descripcion = desc_elem.get_text(strip=True) if desc_elem else title
                
                news_items.append({
                    'titulo': title,
                    'contenido': descripcion,
                    'url': link,
                    'fuente': 'Milenio Monterrey'
                })
            except Exception as e:
                continue
        
        return news_items
    
    def scrape_milenio(self, url: str) -> List[Dict]:
        """Router para diferentes páginas de Milenio."""
        if 'ultima-hora' in url:
            return self.scrape_milenio_ultima_hora(url)
        else:
            return self.scrape_milenio_monterrey(url)
    
    def scrape_generic(self, url: str, source_name: str) -> List[Dict]:
        """Scraper genérico para otros portales."""
        html = self.fetch_page(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        news_items = []
        
        # Buscar artículos con diferentes selectores
        selectors = [
            ('article', {}),
            ('div', {'class': lambda x: x and 'article' in str(x).lower()}),
            ('div', {'class': lambda x: x and 'post' in str(x).lower()}),
            ('div', {'class': lambda x: x and 'news' in str(x).lower()})
        ]
        
        articles = []
        for tag, attrs in selectors:
            articles = soup.find_all(tag, attrs, limit=20)
            if articles:
                break
        
        for article in articles:
            try:
                title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'a'])
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                link_elem = article.find('a', href=True)
                link = link_elem['href'] if link_elem else None
                
                if link and not link.startswith('http'):
                    base_url = '/'.join(url.split('/')[:3])
                    link = f"{base_url}{link}"
                
                if title and len(title) >= 15:
                    news_items.append({
                        'titulo': title,
                        'contenido': title,
                        'url': link,
                        'fuente': source_name
                    })
            except Exception as e:
                continue
        
        return news_items
    
    def scrape_twitter_profile(self, url: str, handle: str) -> List[Dict]:
        """
        Intenta extraer tweets usando Nitter.
        """
        tweets = []
        
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
                tweet_items = soup.find_all('div', class_='timeline-item', limit=10)
                
                for tweet_item in tweet_items:
                    try:
                        tweet_content = tweet_item.find('div', class_='tweet-content')
                        if not tweet_content:
                            continue
                        
                        texto = tweet_content.get_text(strip=True)
                        
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
                
                if tweets:
                    print(f"  ✓ {len(tweets)} tweets extraídos de @{handle}")
                    return tweets
                    
            except Exception as e:
                continue
        
        if not tweets:
            print(f"  ⚠️  No se pudieron obtener tweets de @{handle} (Nitter no disponible)")
        
        return tweets

