"""
Módulo de análisis inteligente de noticias usando OpenAI.
Proporciona análisis avanzado, extracción de ubicaciones y clasificación de severidad.
"""

import os
import json
from typing import Optional, Dict, Tuple
from openai import OpenAI


class AINewsAnalyzer:
    """Clase para análisis inteligente de noticias usando OpenAI."""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Inicializa el analizador de IA.
        
        Args:
            model: Modelo de OpenAI a usar (gpt-4o-mini es más económico y rápido)
        """
        self.client = OpenAI()  # Usa OPENAI_API_KEY del ambiente
        self.model = model
        self.max_tokens = 1000
        self.temperature = 0.1  # Baja temperatura para respuestas más consistentes
    
    def analyze_news(self, title: str, content: str) -> Optional[Dict]:
        """
        Analiza una noticia completa usando IA.
        
        Args:
            title: Título de la noticia
            content: Contenido completo de la noticia
        
        Returns:
            Diccionario con análisis completo o None si falla
        """
        try:
            prompt = self._build_analysis_prompt(title, content)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Eres un asistente experto en análisis de noticias de seguridad y eventos de alto impacto en Monterrey, Nuevo León, México. Respondes siempre en formato JSON válido."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            print(f"⚠️  Error en análisis con IA: {e}")
            return None
    
    def _build_analysis_prompt(self, title: str, content: str) -> str:
        """Construye el prompt para análisis de noticias."""
        return f"""Analiza la siguiente noticia y proporciona un análisis detallado en formato JSON.

TÍTULO: {title}

CONTENIDO: {content[:2000]}

Debes analizar y responder con un JSON que contenga:

1. **is_relevant** (boolean): ¿Es un evento de alto impacto ACTUAL en Monterrey y área metropolitana?
   - SÍ si es: accidente vial, incendio, balacera, bloqueo, desastre natural
   - NO si es: noticia histórica, espectáculos, política general, ubicación lejana

2. **category** (string): Categoría del evento si es relevante:
   - "accidente_vial": choques, volcaduras, atropellos, colisiones
   - "incendio": fuego, llamas, conflagración
   - "seguridad": balaceras, tiroteos, enfrentamientos, detonaciones
   - "bloqueo": manifestaciones, cierres de vialidad, protestas
   - "desastre_natural": inundaciones, trombas, tornados
   - "no_relevante": si no aplica ninguna categoría

3. **severity** (integer 1-10): Gravedad del evento:
   - 1-3: Incidente menor (sin heridos, daños leves)
   - 4-6: Incidente moderado (heridos leves, tráfico afectado)
   - 7-8: Incidente grave (heridos graves, múltiples vehículos, fuego)
   - 9-10: Emergencia crítica (víctimas fatales, peligro inminente)

4. **location** (object): Información de ubicación:
   - **extracted** (string): Ubicación exacta mencionada (calle, avenida, colonia)
   - **normalized** (string): Ubicación normalizada para geocodificación
   - **confidence** (float 0-1): Confianza en la ubicación extraída
   - **is_specific** (boolean): ¿Es ubicación específica o genérica?

5. **summary** (string): Resumen conciso del evento (máximo 100 caracteres)

6. **details** (object):
   - **victims** (integer): Número de víctimas/heridos mencionados (0 si no hay)
   - **traffic_impact** (string): "none", "low", "medium", "high"
   - **emergency_services** (boolean): ¿Hay servicios de emergencia involucrados?
   - **time_reference** (string): "current", "recent", "past", "future"

7. **exclusion_reason** (string o null): Si no es relevante, razón de exclusión

IMPORTANTE:
- Si la noticia menciona "hace años", "en el pasado", "aniversario" → is_relevant: false
- Si habla de espectáculos, actores, celebridades → is_relevant: false
- Si la ubicación es muy genérica como solo "Monterrey" → location.is_specific: false
- Si la ubicación está fuera del área metropolitana (Pesquería, Cadereyta, Santiago) → is_relevant: false

Responde SOLO con el JSON, sin texto adicional."""

    def extract_location_ai(self, text: str) -> Optional[Dict]:
        """
        Extrae ubicación usando IA (método alternativo más rápido).
        
        Args:
            text: Texto de la noticia
        
        Returns:
            Diccionario con información de ubicación
        """
        try:
            prompt = f"""Extrae la ubicación específica de esta noticia de Monterrey, NL:

{text[:1000]}

Responde en JSON con:
- "location": ubicación exacta (calle, avenida, colonia)
- "normalized": ubicación normalizada para búsqueda
- "confidence": confianza 0-1
- "is_specific": true si es ubicación específica, false si es genérica

Si solo menciona "Monterrey" o ubicaciones muy genéricas, marca is_specific como false."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un experto en geografía de Monterrey, NL. Respondes en JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            print(f"⚠️  Error extrayendo ubicación con IA: {e}")
            return None
    
    def classify_severity(self, title: str, content: str) -> int:
        """
        Clasifica la severidad de un evento (método rápido).
        
        Args:
            title: Título de la noticia
            content: Contenido de la noticia
        
        Returns:
            Nivel de severidad (1-10)
        """
        try:
            prompt = f"""Clasifica la severidad de este evento del 1 al 10:

TÍTULO: {title}
CONTENIDO: {content[:500]}

Escala:
1-3: Menor (sin heridos, daños leves)
4-6: Moderado (heridos leves, tráfico afectado)
7-8: Grave (heridos graves, múltiples vehículos)
9-10: Crítico (víctimas fatales, peligro inminente)

Responde en JSON: {{"severity": número}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un analista de emergencias. Respondes en JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=50,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("severity", 5)
            
        except Exception as e:
            print(f"⚠️  Error clasificando severidad: {e}")
            return 5  # Severidad media por defecto
    
    def generate_summary(self, title: str, content: str, max_length: int = 150) -> str:
        """
        Genera un resumen inteligente de la noticia.
        
        Args:
            title: Título de la noticia
            content: Contenido de la noticia
            max_length: Longitud máxima del resumen
        
        Returns:
            Resumen conciso
        """
        try:
            prompt = f"""Resume esta noticia en máximo {max_length} caracteres, enfocándote en:
- QUÉ pasó
- DÓNDE pasó
- Consecuencias principales

TÍTULO: {title}
CONTENIDO: {content[:1000]}

Responde en JSON: {{"summary": "texto del resumen"}}"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un periodista experto en resúmenes concisos. Respondes en JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("summary", title[:max_length])
            
        except Exception as e:
            print(f"⚠️  Error generando resumen: {e}")
            return title[:max_length]
    
    def validate_relevance(self, title: str, content: str) -> Tuple[bool, Optional[str]]:
        """
        Valida si una noticia es relevante para el sistema de monitoreo.
        
        Args:
            title: Título de la noticia
            content: Contenido de la noticia
        
        Returns:
            Tupla (es_relevante, razón_exclusión)
        """
        try:
            prompt = f"""¿Esta noticia es relevante para un sistema de monitoreo de eventos de alto impacto en Monterrey?

TÍTULO: {title}
CONTENIDO: {content[:800]}

Criterios de RELEVANCIA (debe cumplir TODOS):
1. Evento ACTUAL (no histórico, no futuro)
2. Ubicación en Monterrey y área metropolitana (no Pesquería, Cadereyta, Santiago)
3. Alto impacto: accidente, incendio, balacera, bloqueo, desastre
4. NO es espectáculos, farándula, política general

Responde en JSON:
- "is_relevant": true/false
- "reason": razón de exclusión si no es relevante (null si es relevante)"""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Eres un filtro de noticias experto. Respondes en JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=150,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            return result.get("is_relevant", False), result.get("reason")
            
        except Exception as e:
            print(f"⚠️  Error validando relevancia: {e}")
            return True, None  # En caso de error, dejar pasar para análisis manual


# Función de utilidad para análisis rápido
def quick_analyze(title: str, content: str) -> Optional[Dict]:
    """
    Función de utilidad para análisis rápido de una noticia.
    
    Args:
        title: Título de la noticia
        content: Contenido de la noticia
    
    Returns:
        Diccionario con análisis completo
    """
    analyzer = AINewsAnalyzer()
    return analyzer.analyze_news(title, content)


# Ejemplo de uso
if __name__ == "__main__":
    # Prueba del analizador
    analyzer = AINewsAnalyzer()
    
    # Noticia de prueba
    test_title = "Choque en Lázaro Cárdenas deja 3 heridos"
    test_content = """
    Un accidente vehicular en la avenida Lázaro Cárdenas a la altura de Fundadores
    dejó tres personas heridas la tarde de este viernes. El choque involucró dos
    vehículos y causó afectaciones al tránsito en la zona. Elementos de Protección
    Civil y Cruz Roja acudieron al lugar para atender a los lesionados.
    """
    
    print("Analizando noticia de prueba...")
    result = analyzer.analyze_news(test_title, test_content)
    
    if result:
        print("\n✓ Análisis completado:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("\n✗ Error en el análisis")
