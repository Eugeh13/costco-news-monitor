"""
Módulo para filtrar noticias por tiempo de publicación.
Solo permite noticias publicadas en la última hora.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import re
import pytz


class TimeFilter:
    """Clase para filtrar noticias por tiempo de publicación."""
    
    def __init__(self, max_age_hours: int = 1):
        """
        Inicializa el filtro de tiempo.
        
        Args:
            max_age_hours: Antigüedad máxima permitida en horas (default: 1 hora)
        """
        self.max_age_hours = max_age_hours
        self.timezone = pytz.timezone('America/Monterrey')
    
    def get_current_time(self) -> datetime:
        """Obtiene la hora actual en zona horaria de Monterrey."""
        return datetime.now(self.timezone)
    
    def extract_time_from_text(self, text: str) -> Optional[datetime]:
        """
        Extrae información de tiempo del texto de la noticia.
        
        Args:
            text: Texto que puede contener referencias temporales
        
        Returns:
            datetime si se pudo extraer, None en caso contrario
        """
        text_lower = text.lower()
        now = self.get_current_time()
        
        # Primero verificar patrones históricos (rechazo inmediato)
        historical_patterns = [
            r'hace\s+\d+\s+años?',
            r'hace\s+\d+\s+días?',
            r'hace\s+\d+\s+meses?',
            r'hace\s+una\s+década',
            r'hace\s+un\s+mes',
            r'en\s+\d{4}',  # "en 2020", "en 2019"
            r'recordamos',
            r'aniversario',
            r'en\s+el\s+pasado',
            r'así\s+fue',
            r'revelan\s+detalles',
        ]
        
        for pattern in historical_patterns:
            if re.search(pattern, text_lower):
                # Noticia histórica detectada - retornar tiempo muy antiguo
                return now - timedelta(days=365)
        
        # Patrones de tiempo relativo reciente
        patterns = [
            # "hace X minutos"
            (r'hace\s+(\d+)\s+minutos?', 'minutes'),
            # "hace X horas"
            (r'hace\s+(\d+)\s+horas?', 'hours'),
            # "hace X hora"
            (r'hace\s+una\s+hora', 'one_hour'),
            # "hace un momento", "hace momentos"
            (r'hace\s+(?:un\s+)?momentos?', 'moments'),
            # Horas específicas: "10:30", "11:45"
            (r'(\d{1,2}):(\d{2})', 'specific_time'),
        ]
        
        for pattern, time_type in patterns:
            match = re.search(pattern, text_lower)
            if match:
                if time_type == 'minutes':
                    minutes = int(match.group(1))
                    return now - timedelta(minutes=minutes)
                
                elif time_type == 'hours':
                    hours = int(match.group(1))
                    return now - timedelta(hours=hours)
                
                elif time_type == 'one_hour':
                    return now - timedelta(hours=1)
                
                elif time_type == 'moments':
                    return now - timedelta(minutes=5)
                
                elif time_type == 'specific_time':
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    
                    # Crear datetime con la hora específica de hoy
                    news_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    
                    # Si la hora es futura, asumir que es de ayer
                    if news_time > now:
                        news_time = news_time - timedelta(days=1)
                    
                    return news_time
        
        return None
    
    def is_within_time_window(self, news_time: Optional[datetime]) -> bool:
        """
        Verifica si una noticia está dentro de la ventana de tiempo permitida.
        
        Args:
            news_time: Tiempo de publicación de la noticia
        
        Returns:
            True si está dentro de la ventana, False en caso contrario
        """
        if news_time is None:
            # Si no podemos determinar el tiempo, asumimos que es reciente
            # (para no perder noticias por falta de información temporal)
            return True
        
        now = self.get_current_time()
        time_diff = now - news_time
        max_age = timedelta(hours=self.max_age_hours)
        
        return time_diff <= max_age
    
    def filter_news_item(self, news_item: Dict) -> tuple[bool, Optional[str]]:
        """
        Filtra una noticia individual por tiempo.
        
        Args:
            news_item: Diccionario con información de la noticia
        
        Returns:
            Tupla (es_reciente, razón_rechazo)
        """
        titulo = news_item.get('titulo', '')
        contenido = news_item.get('contenido', '')
        
        # Combinar título y contenido para buscar referencias temporales
        text = f"{titulo} {contenido}"
        
        # Intentar extraer tiempo
        news_time = self.extract_time_from_text(text)
        
        # Verificar si está dentro de la ventana
        is_recent = self.is_within_time_window(news_time)
        
        if not is_recent and news_time:
            now = self.get_current_time()
            age_hours = (now - news_time).total_seconds() / 3600
            reason = f"Noticia antigua ({age_hours:.1f} horas)"
            return False, reason
        
        return True, None
    
    def check_with_ai(self, title: str, content: str, ai_analyzer) -> tuple[bool, Optional[str]]:
        """
        Usa IA para verificar si la noticia es actual o histórica.
        
        Args:
            title: Título de la noticia
            content: Contenido de la noticia
            ai_analyzer: Instancia de AINewsAnalyzer
        
        Returns:
            Tupla (es_actual, razón_rechazo)
        """
        try:
            from openai import OpenAI
            
            client = OpenAI()
            
            prompt = f"""Analiza si esta noticia es ACTUAL (de hoy, reciente) o HISTÓRICA (pasada, de hace días/años).

TÍTULO: {title}
CONTENIDO: {content[:500]}

Responde en JSON con:
- "is_current": true si es noticia actual/reciente, false si es histórica
- "time_reference": "current", "recent", "past", "historical"
- "reason": breve explicación

Ejemplos:
- "Choque en Lázaro Cárdenas deja 3 heridos" → is_current: true (no indica tiempo pasado)
- "Hace 5 años ocurrió trágico accidente" → is_current: false (claramente histórica)
- "Recordamos el incendio de 2020" → is_current: false (referencia al pasado)
- "Balacera esta mañana en Cumbres" → is_current: true (indica tiempo reciente)"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un experto en análisis temporal de noticias. Respondes en JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            import json
            result = json.loads(response.choices[0].message.content)
            
            is_current = result.get("is_current", True)
            reason = result.get("reason", "Noticia histórica")
            
            if not is_current:
                return False, reason
            
            return True, None
            
        except Exception as e:
            print(f"⚠️  Error verificando tiempo con IA: {e}")
            # En caso de error, asumir que es actual para no perder noticias
            return True, None
    
    def get_time_window_description(self) -> str:
        """Obtiene descripción de la ventana de tiempo."""
        now = self.get_current_time()
        cutoff_time = now - timedelta(hours=self.max_age_hours)
        
        return f"Noticias desde {cutoff_time.strftime('%H:%M')} hasta {now.strftime('%H:%M')} ({self.max_age_hours}h)"


# Función de utilidad
def is_news_recent(news_item: Dict, max_age_hours: int = 1) -> tuple[bool, Optional[str]]:
    """
    Función de utilidad para verificar si una noticia es reciente.
    
    Args:
        news_item: Diccionario con información de la noticia
        max_age_hours: Antigüedad máxima en horas
    
    Returns:
        Tupla (es_reciente, razón_rechazo)
    """
    filter = TimeFilter(max_age_hours)
    return filter.filter_news_item(news_item)


# Ejemplo de uso
if __name__ == "__main__":
    from datetime import datetime
    
    # Crear filtro de 1 hora
    time_filter = TimeFilter(max_age_hours=1)
    
    print(f"Ventana de tiempo: {time_filter.get_time_window_description()}")
    print()
    
    # Probar con diferentes noticias
    test_cases = [
        {
            'titulo': 'Choque en Lázaro Cárdenas hace 30 minutos',
            'contenido': 'Accidente vehicular reportado hace media hora'
        },
        {
            'titulo': 'Incendio en Cumbres hace 2 horas',
            'contenido': 'Bomberos combaten fuego desde hace 2 horas'
        },
        {
            'titulo': 'Balacera esta mañana en Valle Oriente',
            'contenido': 'Reportan detonaciones en la zona'
        },
        {
            'titulo': 'Hace 5 años ocurrió trágico accidente',
            'contenido': 'Recordamos el accidente que marcó a Monterrey'
        }
    ]
    
    for i, news in enumerate(test_cases, 1):
        is_recent, reason = time_filter.filter_news_item(news)
        status = "✅ RECIENTE" if is_recent else f"❌ RECHAZADA: {reason}"
        print(f"{i}. {news['titulo']}")
        print(f"   {status}")
        print()
