"""
Scraper de Twitter/X con autenticación usando twscrape.
Versión 2.0 - Usa twscrape para mejor compatibilidad con Twitter 2025.
"""

import os
import asyncio
from typing import List, Dict, Optional
from twscrape import API, gather
from twscrape.logger import set_log_level


class TwitterScraperAuth:
    """
    Scraper de Twitter que usa twscrape para autenticación con cookies.
    """
    
    def __init__(self):
        """Inicializa el scraper con configuración de cookies."""
        self.auth_token = os.getenv('TWITTER_AUTH_TOKEN', '')
        self.ct0 = os.getenv('TWITTER_CT0', '')
        self.api = None
        self._initialized = False
        
        # Silenciar logs de twscrape
        set_log_level("ERROR")
    
    def is_configured(self) -> bool:
        """Verifica si las cookies están configuradas."""
        return bool(self.auth_token and self.ct0)
    
    async def _ensure_initialized(self):
        """Inicializa la API de twscrape si no está inicializada."""
        if self._initialized:
            return
        
        if not self.is_configured():
            raise ValueError("Cookies de Twitter no configuradas")
        
        # Crear instancia de API
        self.api = API()
        
        # Formatear cookies para twscrape
        cookies = f"auth_token={self.auth_token}; ct0={self.ct0}"
        
        # Agregar cuenta con cookies
        # Nota: username/password/email no importan cuando usamos cookies
        try:
            await self.api.pool.add_account(
                username="scraper_account",
                password="dummy_password",
                email="dummy@email.com",
                email_password="dummy_email_pass",
                cookies=cookies
            )
            self._initialized = True
        except Exception as e:
            # Si la cuenta ya existe, está bien
            if "UNIQUE constraint failed" in str(e):
                self._initialized = True
            else:
                raise
    
    async def get_user_tweets_async(self, username: str, count: int = 10) -> List[Dict]:
        """
        Obtiene los tweets más recientes de un usuario (versión async).
        
        Args:
            username: Handle del usuario de Twitter (sin @)
            count: Número de tweets a obtener
            
        Returns:
            Lista de diccionarios con información de tweets
        """
        await self._ensure_initialized()
        
        try:
            # Primero obtener el user_id del username
            user_info = await self.api.user_by_login(username)
            if not user_info:
                print(f"⚠️  No se encontró el usuario @{username}")
                return []
            
            user_id = user_info.id
            
            # Ahora obtener tweets usando el user_id
            tweets_generator = self.api.user_tweets(user_id, limit=count)
            tweets = await gather(tweets_generator)
            
            # Convertir a formato compatible con el sistema
            result = []
            for tweet in tweets:
                # Extraer texto del tweet
                text = tweet.rawContent if hasattr(tweet, 'rawContent') else str(tweet)
                
                # Crear diccionario compatible
                tweet_dict = {
                    'titulo': text[:100] + '...' if len(text) > 100 else text,
                    'contenido': text,
                    'url': f"https://twitter.com/{username}/status/{tweet.id}" if hasattr(tweet, 'id') else None,
                    'fuente': f'Twitter @{username}'
                }
                result.append(tweet_dict)
            
            return result
            
        except Exception as e:
            print(f"⚠️  Error obteniendo tweets de @{username}: {e}")
            return []
    
    def get_user_tweets(self, username: str, count: int = 10) -> List[Dict]:
        """
        Obtiene los tweets más recientes de un usuario (versión sincrónica).
        
        Esta es una wrapper sincrónica para usar en código no-async.
        
        Args:
            username: Handle del usuario de Twitter (sin @)
            count: Número de tweets a obtener
            
        Returns:
            Lista de diccionarios con información de tweets
        """
        try:
            # Ejecutar la versión async en un event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    self.get_user_tweets_async(username, count)
                )
                return result
            finally:
                loop.close()
        except Exception as e:
            print(f"⚠️  Error en get_user_tweets: {e}")
            return []


# Función de utilidad para uso directo
def get_tweets(username: str, count: int = 10) -> List[Dict]:
    """
    Función de utilidad para obtener tweets de un usuario.
    
    Args:
        username: Handle del usuario (sin @)
        count: Número de tweets a obtener
        
    Returns:
        Lista de diccionarios con tweets
    """
    scraper = TwitterScraperAuth()
    if not scraper.is_configured():
        print("⚠️  Cookies de Twitter no configuradas")
        return []
    
    return scraper.get_user_tweets(username, count)


if __name__ == "__main__":
    """Script de prueba."""
    import sys
    
    print("=" * 70)
    print("🐦 TWITTER SCRAPER CON TWSCRAPE")
    print("=" * 70)
    print()
    
    scraper = TwitterScraperAuth()
    
    if not scraper.is_configured():
        print("❌ Cookies no configuradas")
        print("Configura TWITTER_AUTH_TOKEN y TWITTER_CT0")
        sys.exit(1)
    
    print("✅ Cookies configuradas")
    print()
    
    # Probar con una cuenta
    test_username = "pc_mty"
    print(f"Obteniendo tweets de @{test_username}...")
    
    tweets = scraper.get_user_tweets(test_username, count=5)
    
    if tweets:
        print(f"✅ {len(tweets)} tweets obtenidos")
        print()
        print("Primer tweet:")
        print(f"  {tweets[0]['titulo']}")
        print(f"  {tweets[0]['url']}")
    else:
        print("❌ No se obtuvieron tweets")
    
    print()
    print("=" * 70)
