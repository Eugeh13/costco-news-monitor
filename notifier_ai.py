"""
Módulo de notificaciones mejorado con soporte para análisis de IA.
"""

import os
import requests
from datetime import datetime
from typing import Dict, Optional


class NotifierAI:
    """Clase mejorada para enviar notificaciones con información de IA."""
    
    def __init__(self, config: dict):
        """
        Inicializa el notificador.
        
        Args:
            config: Diccionario con configuración de notificaciones
        """
        self.config = config
        self.telegram_enabled = config.get('telegram', False)
        self.console_enabled = config.get('console', True)
        
        # Obtener credenciales de Telegram desde variables de entorno
        self.telegram_token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self.telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        
        if self.telegram_enabled and not (self.telegram_token and self.telegram_chat_id):
            print("⚠️  Advertencia: Telegram habilitado pero faltan credenciales")
            self.telegram_enabled = False
    
    def notify(self, data: Dict) -> bool:
        """
        Envía una notificación de alerta.
        
        Args:
            data: Diccionario con información de la noticia
        
        Returns:
            True si se envió correctamente
        """
        success = True
        
        if self.console_enabled:
            self._notify_console(data)
        
        if self.telegram_enabled:
            success = self._notify_telegram(data)
        
        return success
    
    def _notify_console(self, data: Dict):
        """Muestra la notificación en consola."""
        print(f"\n{'='*70}")
        print(f"🚨 ALERTA DE ALTO IMPACTO")
        print(f"{'='*70}")
        print(f"Categoría: {data.get('categoria', 'N/A')}")
        print(f"Título: {data.get('titulo', 'N/A')}")
        print(f"Ubicación: {data.get('ubicacion', 'N/A')}")
        print(f"Distancia: {data.get('distancia_km', 'N/A')} km de {data.get('costco_cercano', 'N/A')}")
        
        # Información adicional de IA si está disponible
        if 'severity' in data:
            print(f"Severidad: {data['severity']}/10 {data.get('severity_emoji', '')}")
        if 'victims' in data and data['victims'] > 0:
            print(f"Víctimas/Heridos: {data['victims']}")
        if 'traffic_impact' in data:
            impact = data['traffic_impact']
            impact_labels = {
                'none': 'Sin impacto',
                'low': 'Bajo',
                'medium': 'Moderado',
                'high': 'Alto'
            }
            print(f"Impacto en tráfico: {impact_labels.get(impact, impact)}")
        if data.get('emergency_services'):
            print(f"Servicios de emergencia: Sí")
        
        print(f"Fuente: {data.get('fuente', 'N/A')}")
        print(f"URL: {data.get('url', 'N/A')}")
        print(f"{'='*70}\n")
    
    def _notify_telegram(self, data: Dict) -> bool:
        """
        Envía notificación a Telegram.
        
        Args:
            data: Diccionario con información de la noticia
        
        Returns:
            True si se envió correctamente
        """
        try:
            # Construir mensaje mejorado con información de IA
            severity_emoji = data.get('severity_emoji', '🚨')
            categoria = data.get('categoria', 'Evento de Alto Impacto')
            titulo = data.get('titulo', 'Sin título')
            ubicacion = data.get('ubicacion', 'Ubicación no especificada')
            distancia = data.get('distancia_km', 'N/A')
            costco = data.get('costco_cercano', 'N/A')
            fuente = data.get('fuente', 'N/A')
            url = data.get('url', '')
            resumen = data.get('resumen', '')
            
            # Construir mensaje base
            message = f"{severity_emoji} *ALERTA COSTCO MTY*\n\n"
            message += f"📍 *{categoria}*\n"
            message += f"📰 {titulo}\n\n"
            
            # Agregar información de severidad si está disponible
            if 'severity' in data:
                severity = data['severity']
                if severity >= 9:
                    severity_label = "CRÍTICA"
                elif severity >= 7:
                    severity_label = "GRAVE"
                elif severity >= 5:
                    severity_label = "MODERADA"
                else:
                    severity_label = "MENOR"
                message += f"⚡ *Severidad: {severity_label}* ({severity}/10)\n"
            
            # Agregar detalles adicionales
            if 'victims' in data and data['victims'] > 0:
                message += f"👥 Víctimas/Heridos: {data['victims']}\n"
            
            if 'traffic_impact' in data:
                impact = data['traffic_impact']
                if impact == 'high':
                    message += f"🚗 Impacto en tráfico: *ALTO*\n"
                elif impact == 'medium':
                    message += f"🚗 Impacto en tráfico: Moderado\n"
                elif impact == 'low':
                    message += f"🚗 Impacto en tráfico: Bajo\n"
            
            if data.get('emergency_services'):
                message += f"🚑 Servicios de emergencia en el lugar\n"
            
            message += f"\n📏 A *{distancia} km* de {costco}\n"
            message += f"🗺️ {ubicacion}\n\n"
            
            # Agregar resumen si está disponible
            if resumen and len(resumen) > 0:
                message += f"📝 {resumen}\n\n"
            
            message += f"📡 {fuente}\n"
            
            if url and url != 'No disponible':
                message += f"🔗 [Ver noticia completa]({url})\n"
            
            timestamp = datetime.now().strftime("%d/%m/%Y %H:%M")
            message += f"\n⏰ {timestamp}"
            
            # Enviar mensaje
            telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': False
            }
            
            response = requests.post(telegram_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✓ Notificación enviada a Telegram")
                return True
            else:
                print(f"⚠️  Error enviando a Telegram: {response.status_code}")
                print(f"   Respuesta: {response.text}")
                return False
                
        except Exception as e:
            print(f"⚠️  Error enviando notificación a Telegram: {e}")
            return False
    
    def send_monitoring_summary(self, data: Dict) -> bool:
        """
        Envía un resumen del monitoreo realizado.
        
        Args:
            data: Diccionario con estadísticas del monitoreo
        
        Returns:
            True si se envió correctamente
        """
        if not self.telegram_enabled:
            return False
        
        try:
            timestamp = data.get('timestamp', datetime.now().strftime("%d/%m/%Y %H:%M"))
            news_analyzed = data.get('news_analyzed', 0)
            alerts_sent = data.get('alerts_sent', 0)
            
            message = "✅ *Monitoreo Completado*\n\n"
            message += "📊 *Resumen:*\n"
            message += f"• Noticias analizadas: {news_analyzed}\n"
            message += f"• Alertas de alto impacto: {alerts_sent}\n"
            
            if alerts_sent == 0:
                message += "• Estado: Todo tranquilo ✓\n"
            
            message += "\n📍 *Áreas monitoreadas:*\n"
            message += "• Costco Carretera Nacional\n"
            message += "• Costco Cumbres\n"
            message += "• Costco Valle Oriente\n"
            
            message += f"\n⏰ {timestamp}\n"
            message += "🔄 Próximo monitoreo en 30 minutos"
            
            telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(telegram_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✓ Resumen enviado a Telegram")
                return True
            else:
                print(f"⚠️  Error enviando resumen: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️  Error enviando resumen: {e}")
            return False
    
    def send_test_message(self) -> bool:
        """
        Envía un mensaje de prueba.
        
        Returns:
            True si se envió correctamente
        """
        if not self.telegram_enabled:
            print("⚠️  Telegram no está habilitado")
            return False
        
        try:
            message = "🤖 *Test del Sistema de Monitoreo*\n\n"
            message += "✓ Sistema con IA funcionando correctamente\n"
            message += "✓ Análisis con OpenAI activo\n"
            message += "✓ Notificaciones operativas\n\n"
            message += f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            
            telegram_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(telegram_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                print("✓ Mensaje de prueba enviado correctamente")
                return True
            else:
                print(f"⚠️  Error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️  Error: {e}")
            return False


# Función de utilidad para pruebas
if __name__ == "__main__":
    import sys
    
    # Configuración de prueba
    config = {
        "console": True,
        "telegram": True
    }
    
    notifier = NotifierAI(config)
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Enviar mensaje de prueba
        notifier.send_test_message()
    else:
        # Enviar notificación de prueba
        test_data = {
            'categoria': 'Accidente Vial',
            'titulo': 'Choque múltiple en Lázaro Cárdenas deja 3 heridos',
            'ubicacion': 'Av. Lázaro Cárdenas altura Fundadores',
            'distancia_km': 2.1,
            'costco_cercano': 'Costco Valle Oriente',
            'costco_direccion': 'Av. Lázaro Cárdenas 800',
            'fuente': 'Milenio Monterrey',
            'url': 'https://www.milenio.com/ejemplo',
            'resumen': 'Accidente vehicular con tres personas lesionadas. Servicios de emergencia en el lugar.',
            'severity': 7,
            'severity_emoji': '🚨',
            'victims': 3,
            'traffic_impact': 'high',
            'emergency_services': True
        }
        
        notifier.notify(test_data)
