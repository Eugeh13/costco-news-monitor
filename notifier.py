"""
Módulo de notificaciones con soporte para Telegram.
"""

from datetime import datetime
from typing import Dict
import os
import requests


class Notifier:
    """Clase para gestionar el envío de notificaciones."""
    
    def __init__(self, config: Dict):
        """
        Inicializa el notificador con la configuración.
        
        Args:
            config: Diccionario con configuración de notificaciones
        """
        self.config = config
        self.telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if config.get('telegram', False):
            if self.telegram_bot_token and self.telegram_chat_id:
                print("✓ Telegram configurado correctamente")
            else:
                print("⚠️  Credenciales de Telegram no encontradas")
                print("   Configure TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID")
    
    def format_notification(self, news_data: Dict) -> str:
        """
        Formatea la información de la noticia en un mensaje legible.
        
        Args:
            news_data: Diccionario con datos de la noticia
        
        Returns:
            Mensaje formateado
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""
{'='*70}
🚨 ALERTA DE NOTICIA DE ALTO IMPACTO 🚨
{'='*70}

📅 Fecha y Hora: {timestamp}
📍 Tipo de Evento: {news_data.get('categoria', 'Desconocido')}
📰 Titular: {news_data.get('titulo', 'Sin título')}

🗺️  Ubicación Detectada: {news_data.get('ubicacion', 'No especificada')}
📏 Proximidad: A {news_data.get('distancia_km', 'N/A')} km de {news_data.get('costco_cercano', 'Costco')}
🏢 Dirección Costco: {news_data.get('costco_direccion', 'N/A')}

📡 Fuente: {news_data.get('fuente', 'Desconocida')}
🔗 URL: {news_data.get('url', 'No disponible')}

📝 Resumen:
{news_data.get('resumen', 'No disponible')}

{'='*70}
"""
        return message
    
    def format_telegram_notification(self, news_data: Dict) -> str:
        """
        Formatea un mensaje para Telegram con formato HTML.
        
        Args:
            news_data: Diccionario con datos de la noticia
        
        Returns:
            Mensaje formateado para Telegram
        """
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
        
        message = f"""🚨 <b>ALERTA COSTCO MTY</b>

📍 <b>{news_data.get('categoria', 'Evento')}</b>
📰 {news_data.get('titulo', 'Sin título')}

📏 A <b>{news_data.get('distancia_km', 'N/A')} km</b> de {news_data.get('costco_cercano', 'Costco')}
🗺️ {news_data.get('ubicacion', 'Ubicación no especificada')}

📡 <i>{news_data.get('fuente', 'Fuente desconocida')}</i>
🔗 <a href="{news_data.get('url', '#')}">Ver noticia completa</a>

⏰ {timestamp}
"""
        return message
    
    def send_console_notification(self, news_data: Dict):
        """
        Imprime la notificación en la consola.
        
        Args:
            news_data: Diccionario con datos de la noticia
        """
        message = self.format_notification(news_data)
        print(message)
    
    def send_telegram_notification(self, news_data: Dict) -> bool:
        """
        Envía notificación por Telegram.
        
        Args:
            news_data: Diccionario con datos de la noticia
        
        Returns:
            True si se envió correctamente, False en caso contrario
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("⚠️  Telegram no configurado. Mensaje no enviado.")
            return False
        
        try:
            message = self.format_telegram_notification(news_data)
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Mensaje de Telegram enviado correctamente")
                return True
            else:
                print(f"❌ Error enviando mensaje de Telegram: {response.text}")
                return False
            
        except Exception as e:
            print(f"❌ Error enviando mensaje de Telegram: {e}")
            return False
    
    def send_monitoring_summary(self, summary_data: Dict):
        """
        Envía un resumen del monitoreo realizado.
        
        Args:
            summary_data: Diccionario con datos del resumen
        """
        if not self.telegram_bot_token or not self.telegram_chat_id:
            return
        
        timestamp = summary_data.get('timestamp')
        news_analyzed = summary_data.get('news_analyzed', 0)
        alerts_sent = summary_data.get('alerts_sent', 0)
        
        try:
            message = f"""✅ <b>Monitoreo Completado</b>

📊 <b>Resumen:</b>
• Noticias analizadas: {news_analyzed}
• Alertas de alto impacto: {alerts_sent}
• Estado: Todo tranquilo ✓

📍 <b>Áreas monitoreadas:</b>
• Costco Carretera Nacional
• Costco Cumbres
• Costco Valle Oriente

⏰ {timestamp}
🔄 Próximo monitoreo en 30 minutos"""
            
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print(f"✓ Resumen de monitoreo enviado a Telegram")
            else:
                print(f"❌ Error enviando resumen: {response.text}")
        
        except Exception as e:
            print(f"❌ Error enviando resumen: {e}")
    
    def notify(self, news_data: Dict):
        """
        Envía notificaciones según la configuración.
        
        Args:
            news_data: Diccionario con datos de la noticia
        """
        if self.config.get('console', True):
            self.send_console_notification(news_data)
        
        if self.config.get('telegram', False):
            self.send_telegram_notification(news_data)

