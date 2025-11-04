"""
Scraper de Twitter/X usando autenticación con cookies de sesión.
"""

import requests
import json
import os
from typing import List, Dict, Optional
from datetime import datetime
import time


class TwitterScraperAuth:
    """Scraper de Twitter que usa cookies de sesión para autenticación."""
    
    def __init__(self):
        """Inicializa el scraper con cookies de las variables de entorno."""
        self.auth_token = os.getenv('TWITTER_AUTH_TOKEN', '')
        self.ct0 = os.getenv('TWITTER_CT0', '')
        
        # Headers que simulan un navegador real
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'es-MX,es;q=0.9,en;q=0.8',
            'Referer': 'https://twitter.com/',
            'x-twitter-active-user': 'yes',
            'x-twitter-client-language': 'es',
        }
        
        # Agregar cookies si están disponibles
        if self.ct0:
            self.headers['x-csrf-token'] = self.ct0
        
        # Cookies para la sesión
        self.cookies = {}
        if self.auth_token:
            self.cookies['auth_token'] = self.auth_token
        if self.ct0:
            self.cookies['ct0'] = self.ct0
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.session.cookies.update(self.cookies)
    
    def is_configured(self) -> bool:
        """Verifica si las cookies están configuradas."""
        return bool(self.auth_token and self.ct0)
    
    def get_user_tweets(self, username: str, count: int = 20) -> List[Dict]:
        """
        Obtiene los tweets recientes de un usuario.
        
        Args:
            username: Nombre de usuario sin @
            count: Número de tweets a obtener
        
        Returns:
            Lista de diccionarios con información de tweets
        """
        if not self.is_configured():
            print(f"⚠️  Twitter scraping no configurado (faltan cookies)")
            return []
        
        try:
            # Primero obtener el user_id del username
            user_id = self._get_user_id(username)
            if not user_id:
                return []
            
            # Luego obtener los tweets
            tweets = self._get_tweets_by_user_id(user_id, count)
            
            # Convertir a formato compatible con el sistema
            news_items = []
            for tweet in tweets:
                news_items.append({
                    'titulo': tweet.get('text', '')[:200],  # Primeros 200 caracteres
                    'contenido': tweet.get('text', ''),
                    'url': f"https://twitter.com/{username}/status/{tweet.get('id', '')}",
                    'fuente': f'Twitter @{username}'
                })
            
            return news_items
            
        except Exception as e:
            print(f"⚠️  Error obteniendo tweets de @{username}: {e}")
            return []
    
    def _get_user_id(self, username: str) -> Optional[str]:
        """Obtiene el user_id de un username."""
        try:
            # Usar la API GraphQL de Twitter para obtener info del usuario
            url = "https://twitter.com/i/api/graphql/sLVLhk0bGj3MVFEKTdax1w/UserByScreenName"
            
            variables = {
                "screen_name": username,
                "withSafetyModeUserFields": True
            }
            
            features = {
                "hidden_profile_likes_enabled": True,
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "subscriptions_verification_info_verified_since_enabled": True,
                "highlights_tweets_tab_ui_enabled": True,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "responsive_web_graphql_timeline_navigation_enabled": True
            }
            
            params = {
                'variables': json.dumps(variables),
                'features': json.dumps(features)
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                user_id = data.get('data', {}).get('user', {}).get('result', {}).get('rest_id')
                return user_id
            else:
                print(f"⚠️  Error obteniendo user_id de @{username}: Status {response.status_code}")
                return None
                
        except Exception as e:
            print(f"⚠️  Error en _get_user_id para @{username}: {e}")
            return None
    
    def _get_tweets_by_user_id(self, user_id: str, count: int) -> List[Dict]:
        """Obtiene tweets de un usuario por su ID."""
        try:
            # Usar la API GraphQL de Twitter para obtener tweets
            url = "https://twitter.com/i/api/graphql/V7H0Ap3_Hh2FyS75OCDO3Q/UserTweets"
            
            variables = {
                "userId": user_id,
                "count": count,
                "includePromotedContent": False,
                "withQuickPromoteEligibilityTweetFields": False,
                "withVoice": False,
                "withV2Timeline": True
            }
            
            features = {
                "responsive_web_graphql_exclude_directive_enabled": True,
                "verified_phone_label_enabled": False,
                "creator_subscriptions_tweet_preview_api_enabled": True,
                "responsive_web_graphql_timeline_navigation_enabled": True,
                "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                "tweetypie_unmention_optimization_enabled": True,
                "responsive_web_edit_tweet_api_enabled": True,
                "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
                "view_counts_everywhere_api_enabled": True,
                "longform_notetweets_consumption_enabled": True,
                "responsive_web_twitter_article_tweet_consumption_enabled": False,
                "tweet_awards_web_tipping_enabled": False,
                "freedom_of_speech_not_reach_fetch_enabled": True,
                "standardized_nudges_misinfo": True,
                "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
                "longform_notetweets_rich_text_read_enabled": True,
                "longform_notetweets_inline_media_enabled": True,
                "responsive_web_media_download_video_enabled": False,
                "responsive_web_enhance_cards_enabled": False
            }
            
            params = {
                'variables': json.dumps(variables),
                'features': json.dumps(features)
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extraer tweets del response
                tweets = []
                instructions = data.get('data', {}).get('user', {}).get('result', {}).get('timeline_v2', {}).get('timeline', {}).get('instructions', [])
                
                for instruction in instructions:
                    if instruction.get('type') == 'TimelineAddEntries':
                        entries = instruction.get('entries', [])
                        for entry in entries:
                            if entry.get('content', {}).get('entryType') == 'TimelineTimelineItem':
                                tweet_result = entry.get('content', {}).get('itemContent', {}).get('tweet_results', {}).get('result', {})
                                
                                if tweet_result.get('__typename') == 'Tweet':
                                    legacy = tweet_result.get('legacy', {})
                                    tweet_id = tweet_result.get('rest_id', '')
                                    text = legacy.get('full_text', '')
                                    created_at = legacy.get('created_at', '')
                                    
                                    tweets.append({
                                        'id': tweet_id,
                                        'text': text,
                                        'created_at': created_at
                                    })
                
                return tweets[:count]
            else:
                print(f"⚠️  Error obteniendo tweets: Status {response.status_code}")
                return []
                
        except Exception as e:
            print(f"⚠️  Error en _get_tweets_by_user_id: {e}")
            return []
    
    def scrape_accounts(self, accounts: List[str], tweets_per_account: int = 10) -> List[Dict]:
        """
        Scraping de múltiples cuentas de Twitter.
        
        Args:
            accounts: Lista de usernames (sin @)
            tweets_per_account: Tweets a obtener por cuenta
        
        Returns:
            Lista combinada de todos los tweets
        """
        if not self.is_configured():
            print("⚠️  Twitter scraping no configurado. Configura TWITTER_AUTH_TOKEN y TWITTER_CT0")
            return []
        
        all_tweets = []
        
        for username in accounts:
            print(f"Monitoreando: @{username}...")
            tweets = self.get_user_tweets(username, tweets_per_account)
            all_tweets.extend(tweets)
            print(f"  → {len(tweets)} tweets encontrados")
            
            # Delay entre cuentas para no saturar
            time.sleep(2)
        
        return all_tweets


# Función de utilidad
def get_twitter_news(accounts: List[str] = None, tweets_per_account: int = 10) -> List[Dict]:
    """
    Función de utilidad para obtener tweets de cuentas específicas.
    
    Args:
        accounts: Lista de usernames, por defecto usa cuentas de Monterrey
        tweets_per_account: Tweets por cuenta
    
    Returns:
        Lista de tweets en formato de noticias
    """
    if accounts is None:
        accounts = ['pc_mty', 'mtytrafico', 'seguridadmtymx']
    
    scraper = TwitterScraperAuth()
    return scraper.scrape_accounts(accounts, tweets_per_account)


# Ejemplo de uso
if __name__ == "__main__":
    print("🐦 Twitter Scraper con Autenticación")
    print("=" * 60)
    
    scraper = TwitterScraperAuth()
    
    if not scraper.is_configured():
        print("\n⚠️  CONFIGURACIÓN REQUERIDA:")
        print("\nPara usar este scraper, necesitas configurar las siguientes")
        print("variables de entorno:")
        print("\n1. TWITTER_AUTH_TOKEN")
        print("2. TWITTER_CT0")
        print("\nEstas son cookies de tu sesión de Twitter/X.")
        print("\nInstrucciones:")
        print("1. Abre Twitter/X en tu navegador")
        print("2. Inicia sesión")
        print("3. Presiona F12 (DevTools)")
        print("4. Ve a Application > Cookies > https://twitter.com")
        print("5. Copia los valores de 'auth_token' y 'ct0'")
        print("6. Configúralos como variables de entorno")
    else:
        print("\n✅ Cookies configuradas correctamente")
        print("\nProbando scraping de @pc_mty...")
        
        tweets = scraper.get_user_tweets('pc_mty', 5)
        
        print(f"\n📊 Resultados: {len(tweets)} tweets")
        for i, tweet in enumerate(tweets, 1):
            print(f"\n{i}. {tweet['titulo'][:100]}...")
            print(f"   URL: {tweet['url']}")
