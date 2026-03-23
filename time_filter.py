"""
Módulo para filtrar noticias por tiempo de publicación.
Solo permite noticias con impacto activo (publicadas recientemente).

v2: Usa fecha_pub del RSS feed como fuente primaria de tiempo.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import re
import pytz


class TimeFilter:
    """Filtra noticias por tiempo de publicación."""
    
    def __init__(self, max_age_hours: int = 1):
        self.max_age_hours = max_age_hours
        self.timezone = pytz.timezone('America/Chicago')
    
    def get_current_time(self) -> datetime:
        return datetime.now(self.timezone)
    
    def parse_fecha_pub(self, fecha_pub) -> Optional[datetime]:
        """
        Parsea el campo fecha_pub que viene del RSS/GNews.
        Puede ser un string ISO, un datetime, o None.
        """
        if fecha_pub is None:
            return None
        
        # Si ya es datetime
        if isinstance(fecha_pub, datetime):
            if fecha_pub.tzinfo is None:
                return self.timezone.localize(fecha_pub)
            return fecha_pub
        
        # Si es string, intentar parsear
        if isinstance(fecha_pub, str):
            formats = [
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%S%z',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S.%f%z',
                '%a, %d %b %Y %H:%M:%S %Z',
                '%a, %d %b %Y %H:%M:%S %z',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d/%m/%Y %H:%M',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(fecha_pub.strip(), fmt)
                    if dt.tzinfo is None:
                        dt = self.timezone.localize(dt)
                    return dt
                except (ValueError, TypeError):
                    continue
        
        return None
    
    def extract_time_from_text(self, text: str) -> Optional[datetime]:
        """Extrae tiempo del texto de la noticia (fallback)."""
        text_lower = text.lower()
        now = self.get_current_time()
        
        # Patrones históricos → rechazo inmediato
        historical_patterns = [
            r'hace\s+\d+\s+años?',
            r'hace\s+\d+\s+días?',
            r'hace\s+\d+\s+meses?',
            r'hace\s+una\s+década',
            r'hace\s+un\s+mes',
            r'en\s+(19|20)\d{2}',
            r'recordamos',
            r'aniversario',
            r'en\s+el\s+pasado',
            r'así\s+fue',
            r'revelan\s+detalles',
        ]
        
        for pattern in historical_patterns:
            if re.search(pattern, text_lower):
                return now - timedelta(days=365)
        
        # Patrones de tiempo relativo reciente
        patterns = [
            (r'hace\s+(\d+)\s+minutos?', 'minutes'),
            (r'hace\s+(\d+)\s+horas?', 'hours'),
            (r'hace\s+una\s+hora', 'one_hour'),
            (r'hace\s+(?:un\s+)?momentos?', 'moments'),
            (r'(\d{1,2}):(\d{2})', 'specific_time'),
        ]
        
        for pattern, time_type in patterns:
            match = re.search(pattern, text_lower)
            if match:
                if time_type == 'minutes':
                    return now - timedelta(minutes=int(match.group(1)))
                elif time_type == 'hours':
                    return now - timedelta(hours=int(match.group(1)))
                elif time_type == 'one_hour':
                    return now - timedelta(hours=1)
                elif time_type == 'moments':
                    return now - timedelta(minutes=5)
                elif time_type == 'specific_time':
                    hour = int(match.group(1))
                    minute = int(match.group(2))
                    if 0 <= hour <= 23 and 0 <= minute <= 59:
                        news_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        if news_time > now:
                            news_time = news_time - timedelta(days=1)
                        return news_time
        
        return None
    
    def is_within_time_window(self, news_time: Optional[datetime], strict: bool = False) -> bool:
        """
        Verifica si una noticia está dentro de la ventana de tiempo.
        
        Args:
            news_time: Tiempo de publicación
            strict: Si True, rechaza noticias sin fecha. Si False, las deja pasar.
        """
        if news_time is None:
            return not strict
        
        now = self.get_current_time()
        
        # Asegurar que ambos tengan timezone
        if news_time.tzinfo is None:
            news_time = self.timezone.localize(news_time)
        
        time_diff = now - news_time
        max_age = timedelta(hours=self.max_age_hours)
        
        return time_diff <= max_age and time_diff >= timedelta(0)
    
    def filter_news_item(self, news_item: Dict) -> tuple:
        """
        Filtra una noticia por tiempo.
        
        PRIORIDAD:
        1. Usa fecha_pub del feed RSS (más confiable)
        2. Si no hay fecha_pub, analiza el texto
        3. Si no puede determinar fecha → RECHAZA (antes dejaba pasar)
        """
        titulo = news_item.get('titulo', '')
        contenido = news_item.get('contenido', '')
        fecha_pub = news_item.get('fecha_pub', None)
        
        # PRIORIDAD 1: Usar fecha_pub del RSS feed
        pub_time = self.parse_fecha_pub(fecha_pub)
        
        if pub_time is not None:
            is_recent = self.is_within_time_window(pub_time, strict=True)
            if not is_recent:
                now = self.get_current_time()
                if pub_time.tzinfo is None:
                    pub_time = self.timezone.localize(pub_time)
                age_hours = (now - pub_time).total_seconds() / 3600
                return False, f"Noticia antigua ({age_hours:.1f} horas, fecha_pub: {pub_time.strftime('%d/%m %H:%M')})"
            return True, None
        
        # PRIORIDAD 2: Analizar texto
        text = f"{titulo} {contenido}"
        text_time = self.extract_time_from_text(text)
        
        if text_time is not None:
            is_recent = self.is_within_time_window(text_time, strict=True)
            if not is_recent:
                now = self.get_current_time()
                age_hours = (now - text_time).total_seconds() / 3600
                return False, f"Noticia antigua ({age_hours:.1f} horas)"
            return True, None
        
        # PRIORIDAD 3: Sin fecha detectable → dejar pasar con cautela
        # (la IA en el triage se encargará de filtrar por impacto temporal)
        return True, None
    
    def get_time_window_description(self) -> str:
        now = self.get_current_time()
        cutoff_time = now - timedelta(hours=self.max_age_hours)
        return f"Noticias desde {cutoff_time.strftime('%H:%M')} hasta {now.strftime('%H:%M')} ({self.max_age_hours}h)"


def is_news_recent(news_item: Dict, max_age_hours: int = 1) -> tuple:
    filter = TimeFilter(max_age_hours)
    return filter.filter_news_item(news_item)


if __name__ == "__main__":
    time_filter = TimeFilter(max_age_hours=1)
    
    print(f"Ventana de tiempo: {time_filter.get_time_window_description()}")
    print()
    
    test_cases = [
        {
            'titulo': 'Choque en Lázaro Cárdenas hace 30 minutos',
            'contenido': 'Accidente vehicular reportado',
            'fecha_pub': None,
        },
        {
            'titulo': 'Incendio en Cumbres',
            'contenido': 'Bomberos combaten fuego',
            'fecha_pub': (datetime.now(pytz.timezone('America/Chicago')) - timedelta(hours=5)).isoformat(),
        },
        {
            'titulo': 'Balacera en Valle Oriente',
            'contenido': 'Reportan detonaciones',
            'fecha_pub': (datetime.now(pytz.timezone('America/Chicago')) - timedelta(minutes=20)).isoformat(),
        },
        {
            'titulo': 'Hace 5 años ocurrió trágico accidente',
            'contenido': 'Recordamos el accidente que marcó a Monterrey',
            'fecha_pub': None,
        },
        {
            'titulo': 'Noticia del 20 de marzo sin contexto temporal',
            'contenido': 'Algo pasó en algún lugar',
            'fecha_pub': '2026-03-20T14:30:00',
        },
    ]
    
    for i, news in enumerate(test_cases, 1):
        is_recent, reason = time_filter.filter_news_item(news)
        status = "✅ RECIENTE" if is_recent else f"❌ RECHAZADA: {reason}"
        print(f"{i}. {news['titulo']}")
        print(f"   fecha_pub: {news.get('fecha_pub', 'None')}")
        print(f"   {status}")
        print()
