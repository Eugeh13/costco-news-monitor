"""
Módulo de análisis y filtrado de noticias.
"""

import re
from typing import Optional, Tuple, List


class NewsAnalyzer:
    """Clase para analizar y filtrar noticias de alto impacto."""
    
    def __init__(self, keywords: dict):
        """
        Inicializa el analizador con las palabras clave.
        
        Args:
            keywords: Diccionario con categorías y palabras clave
        """
        self.keywords = keywords
    
    def check_high_impact(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica si un texto contiene palabras clave de alto impacto.
        
        Args:
            text: Texto a analizar (titular o contenido)
        
        Returns:
            Tupla (es_alto_impacto, categoría)
        """
        text_lower = text.lower()
        
        # Primero, verificar si contiene palabras de exclusión
        import config
        for exclusion_word in config.EXCLUSION_KEYWORDS:
            if exclusion_word in text_lower:
                return (False, None)
        
        # Luego, buscar palabras clave de alto impacto
        for category, words in self.keywords.items():
            for word in words:
                if word in text_lower:
                    return (True, category)
        
        return (False, None)
    
    def extract_location(self, text: str) -> Optional[str]:
        """
        Extrae información de ubicación del texto.
        
        Args:
            text: Texto de la noticia
        
        Returns:
            String con la ubicación extraída o None
        """
        # Patrones comunes para ubicaciones en Monterrey
        patterns = [
            # Avenidas y calles
            r'(?:av\.|avenida|calle|c\.|blvd\.|boulevard)\s+([a-záéíóúñ\s]+?)(?:\s+(?:y|con|cruce|esquina)\s+(?:av\.|avenida|calle|c\.)\s+([a-záéíóúñ\s]+?))?(?:\s+en|\s+col\.|,|\.|$)',
            # Colonias
            r'(?:colonia|col\.)\s+([a-záéíóúñ\s]+?)(?:,|\.|$)',
            # Cruces o intersecciones
            r'cruce\s+(?:de\s+)?([a-záéíóúñ\s]+?)\s+(?:y|con)\s+([a-záéíóúñ\s]+?)(?:,|\.|$)',
            # Kilómetro en carretera
            r'carretera\s+([a-záéíóúñ\s]+?)\s+(?:km|kilómetro)\s+(\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text.lower())
            if match:
                # Construir ubicación a partir de los grupos capturados
                location_parts = [g.strip() for g in match.groups() if g]
                if location_parts:
                    return ' '.join(location_parts)
        
        # Buscar nombres de colonias y municipios conocidos de Monterrey
        # Dividir en áreas específicas (aceptables) y genéricas (rechazar)
        specific_areas = [
            'cumbres', 'valle oriente', 'san pedro', 'santa catarina',
            'guadalupe', 'san nicolás', 'apodaca', 'mitras',
            'contry', 'del valle', 'san pedro garza garcía', 'garza garcía',
            'carretera nacional', 'loma larga', 'gonzalitos', 'constitución',
            'lázaro cárdenas', 'fundadores', 'vasconcelos', 'gómez morín',
            'alejandro de rodas', 'rangel frías', 'bernardo reyes', 'madero',
            'morones prieto', 'paseo de los leones'
        ]
        
        # Ubicaciones genéricas que NO son suficientes (rechazar)
        generic_areas = ['monterrey', 'centro', 'nuevo león', ' nl ', 'residencial', 'industrial']
        
        text_lower = text.lower()
        
        # Primero buscar áreas específicas
        for area in specific_areas:
            if area in text_lower:
                return area
        
        # Si solo encuentra áreas genéricas, rechazar
        for area in generic_areas:
            if area in text_lower:
                # Retornar None para forzar que se busque ubicación más específica
                return None
        
        return None
    
    def extract_category_label(self, category: str) -> str:
        """
        Convierte el nombre de categoría en una etiqueta legible.
        
        Args:
            category: Nombre de la categoría
        
        Returns:
            Etiqueta legible
        """
        labels = {
            'accidente_vial': 'Accidente Vial',
            'incendio': 'Incendio',
            'seguridad': 'Situación de Seguridad',
            'bloqueo': 'Bloqueo de Vialidad',
            'desastre_natural': 'Desastre Natural'
        }
        return labels.get(category, category)

