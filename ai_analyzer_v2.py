"""
Módulo de análisis inteligente v2 - Agente IA con triage.

Arquitectura de 2 pasos:
1. TRIAGE RÁPIDO: Recibe batch de títulos, descarta irrelevantes en una sola llamada
2. ANÁLISIS PROFUNDO: Solo para candidatas, análisis completo con structured output

Soporta:
- OpenAI (GPT-4o-mini) - default, más barato para triage
- Anthropic Claude (Sonnet) - opcional, mejor razonamiento

Optimización de costos:
- Triage: 1 llamada IA por batch (~20-50 noticias) en vez de 1 por noticia
- Análisis profundo: solo ~5-10% de las noticias pasan el triage
"""

import os
import json
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

# OpenAI (default)
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Anthropic (opcional)
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


@dataclass
class TriageResult:
    """Resultado del triage rápido para una noticia."""
    index: int
    is_candidate: bool
    reason: str
    estimated_category: str  # accidente, incendio, seguridad, bloqueo, desastre, otro
    estimated_severity: int  # 1-10 estimado
    location_hint: str       # Ubicación mencionada (puede ser vaga)


@dataclass
class DeepAnalysisResult:
    """Resultado del análisis profundo."""
    is_relevant: bool
    category: str
    severity: int
    location: dict
    summary: str
    details: dict
    exclusion_reason: Optional[str]


class AIAnalyzerV2:
    """
    Analizador de IA con triage inteligente.
    
    Flujo:
    1. batch_triage() - Filtra noticias irrelevantes en una sola llamada
    2. deep_analyze() - Análisis completo solo para candidatas
    """
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
        """
        Args:
            provider: "openai" o "anthropic"
            model: Modelo específico. Default: gpt-4o-mini (openai) o claude-sonnet-4-20250514 (anthropic)
        """
        self.provider = provider.lower()
        
        if self.provider == "openai":
            if not OPENAI_AVAILABLE:
                raise ImportError("pip install openai")
            self.client = OpenAI()
            self.model = model or "gpt-4o-mini"
            
        elif self.provider == "anthropic":
            if not ANTHROPIC_AVAILABLE:
                raise ImportError("pip install anthropic")
            self.client = anthropic.Anthropic()
            self.model = model or "claude-sonnet-4-20250514"
        else:
            raise ValueError(f"Provider no soportado: {provider}. Usa 'openai' o 'anthropic'")
        
        print(f"  ✓ AI Analyzer v2: {self.provider} / {self.model}")
    
    # ========================================================
    # Capa de abstracción para llamadas a IA
    # ========================================================
    
    def _call_ai(self, system_prompt: str, user_prompt: str, 
                 max_tokens: int = 1000, temperature: float = 0.1) -> Optional[str]:
        """Llama al modelo de IA configurado. Retorna texto de respuesta."""
        try:
            if self.provider == "openai":
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"}
                )
                return response.choices[0].message.content
                
            elif self.provider == "anthropic":
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt + "\n\nIMPORTANTE: Responde SOLO con JSON válido, sin texto adicional.",
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                )
                return response.content[0].text
                
        except Exception as e:
            print(f"  ⚠️ Error en llamada IA ({self.provider}): {e}")
            return None
    
    def _parse_json(self, text: str) -> Optional[dict]:
        """Parsea JSON de la respuesta, con limpieza."""
        if not text:
            return None
        try:
            # Limpiar posibles artefactos
            text = text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            print(f"  ⚠️ Error parseando JSON: {e}")
            print(f"  Respuesta: {text[:200]}...")
            return None

    # ========================================================
    # PASO 1: Triage rápido (batch)
    # ========================================================
    
    def batch_triage(self, news_items: List[dict]) -> List[TriageResult]:
        """
        Filtra un batch de noticias en UNA SOLA llamada a la IA.
        
        En vez de hacer 30-50 llamadas individuales, enviamos todos los títulos
        en un solo prompt y la IA clasifica cuáles son candidatas.
        
        Args:
            news_items: Lista de dicts con 'titulo' y opcionalmente 'contenido'
        
        Returns:
            Lista de TriageResult para cada noticia
        
        Costo estimado: ~$0.001-0.003 USD por batch de 50 noticias
        """
        if not news_items:
            return []
        
        # Construir lista numerada de titulares
        titulares = []
        for i, item in enumerate(news_items):
            titulo = item.get('titulo', '')[:120]
            snippet = item.get('contenido', '')[:80]
            titulares.append(f"{i}: {titulo} | {snippet}")
        
        titulares_text = "\n".join(titulares)
        
        system_prompt = """Eres un filtro de noticias experto para un sistema de monitoreo de emergencias 
en Monterrey, Nuevo León, México. Tu trabajo es hacer triage RÁPIDO de titulares.

Respondes en JSON."""

        user_prompt = f"""Analiza estos {len(news_items)} titulares de noticias y clasifica cuáles son CANDIDATAS 
para un sistema de monitoreo de emergencias cerca de sucursales Costco en Monterrey, NL.

TITULARES:
{titulares_text}

CRITERIOS para ser CANDIDATA (debe cumplir TODOS):
1. Es un evento de ALTO IMPACTO: accidente vial, incendio, balacera, bloqueo, desastre natural
2. Ocurrió en MONTERREY o su área metropolitana (San Pedro, San Nicolás, Guadalupe, Apodaca, Santa Catarina, Escobedo, García)
3. Es RECIENTE/ACTUAL (no histórica, no programada a futuro)
4. NO es: espectáculos, deportes, política general, opinión, economía general

EXCLUIR inmediatamente:
- Noticias de otras ciudades/estados (CDMX, Guadalajara, etc.)
- Noticias históricas ("hace 5 años", "aniversario de")
- Farándula, entretenimiento, deportes
- Política general, economía sin impacto local directo

Responde con JSON:
{{
  "results": [
    {{
      "index": 0,
      "is_candidate": true/false,
      "reason": "razón breve (max 15 palabras)",
      "category": "accidente_vial|incendio|seguridad|bloqueo|desastre_natural|no_relevante",
      "severity_estimate": 1-10,
      "location_hint": "ubicación mencionada o 'no_especifica'"
    }}
  ]
}}

IMPORTANTE: Incluye TODOS los {len(news_items)} titulares en la respuesta, no omitas ninguno."""

        result_text = self._call_ai(
            system_prompt, 
            user_prompt, 
            max_tokens=min(4000, len(news_items) * 80),  # Escalar tokens al batch
            temperature=0.1
        )
        
        parsed = self._parse_json(result_text)
        if not parsed or 'results' not in parsed:
            print(f"  ⚠️ Triage falló, marcando todas como candidatas (fallback)")
            return [
                TriageResult(
                    index=i, is_candidate=True, reason="triage_fallback",
                    estimated_category="desconocido", estimated_severity=5,
                    location_hint="no_especifica"
                )
                for i in range(len(news_items))
            ]
        
        triage_results = []
        for item in parsed['results']:
            triage_results.append(TriageResult(
                index=item.get('index', 0),
                is_candidate=item.get('is_candidate', False),
                reason=item.get('reason', ''),
                estimated_category=item.get('category', 'no_relevante'),
                estimated_severity=item.get('severity_estimate', 5),
                location_hint=item.get('location_hint', 'no_especifica'),
            ))
        
        candidates = sum(1 for r in triage_results if r.is_candidate)
        print(f"  🤖 Triage: {candidates}/{len(news_items)} candidatas")
        
        return triage_results

    # ========================================================
    # PASO 2: Análisis profundo (individual)
    # ========================================================
    
    def deep_analyze(self, title: str, content: str) -> Optional[Dict]:
        """
        Análisis profundo de una noticia candidata.
        
        Solo se llama para noticias que pasaron el triage.
        Extrae: relevancia, categoría, severidad, ubicación precisa, resumen, detalles.
        
        Args:
            title: Título de la noticia
            content: Contenido completo del artículo
        
        Returns:
            Dict con análisis completo o None si falla
        """
        system_prompt = """Eres un analista experto en seguridad y emergencias de Monterrey, Nuevo León, México. 
Analizas noticias para un sistema de monitoreo cerca de sucursales Costco.
Respondes en JSON."""

        user_prompt = f"""Analiza esta noticia en detalle:

TÍTULO: {title}
CONTENIDO: {content[:2500]}

Responde con este JSON EXACTO:
{{
  "is_relevant": true/false,
  "category": "accidente_vial|incendio|seguridad|bloqueo|desastre_natural|no_relevante",
  "severity": 1-10,
  "location": {{
    "extracted": "ubicación exacta (calle, avenida, colonia, cruce)",
    "normalized": "ubicación para geocodificación (ej: 'Av Lázaro Cárdenas y Fundadores, San Pedro Garza García, NL')",
    "municipality": "municipio (Monterrey|San Pedro|San Nicolás|Guadalupe|Apodaca|Santa Catarina|Escobedo|García|otro)",
    "confidence": 0.0-1.0,
    "is_specific": true/false
  }},
  "summary": "resumen en max 100 caracteres",
  "details": {{
    "victims": 0,
    "traffic_impact": "none|low|medium|high",
    "emergency_services": true/false,
    "time_reference": "current|recent|past|future",
    "affected_roads": ["lista de vialidades afectadas"]
  }},
  "exclusion_reason": null o "razón si no es relevante"
}}

REGLAS:
- severity 1-3: menor (sin heridos, daños leves)
- severity 4-6: moderado (heridos leves, tráfico afectado)
- severity 7-8: grave (heridos graves, múltiples vehículos, fuego activo)
- severity 9-10: crítico (víctimas fatales, peligro inminente)
- Si la ubicación es genérica ("Monterrey"), marca is_specific: false
- Si es noticia histórica, is_relevant: false
- affected_roads: lista las vialidades principales mencionadas"""

        result_text = self._call_ai(system_prompt, user_prompt, max_tokens=800, temperature=0.1)
        result = self._parse_json(result_text)
        
        return result

    # ========================================================
    # Métodos de compatibilidad con ai_analyzer.py original
    # ========================================================
    
    def analyze_news(self, title: str, content: str) -> Optional[Dict]:
        """Compatible con AINewsAnalyzer.analyze_news()"""
        return self.deep_analyze(title, content)
    
    def extract_location_ai(self, text: str) -> Optional[Dict]:
        """Extrae ubicación de un texto."""
        system_prompt = "Eres un experto en geografía de Monterrey, NL. Respondes en JSON."
        user_prompt = f"""Extrae la ubicación de esta noticia de Monterrey:

{text[:1000]}

JSON: {{"location": "ubicación exacta", "normalized": "para geocodificar", "confidence": 0-1, "is_specific": true/false}}"""
        
        result_text = self._call_ai(system_prompt, user_prompt, max_tokens=200)
        return self._parse_json(result_text)
    
    def classify_severity(self, title: str, content: str) -> int:
        """Clasifica severidad rápidamente."""
        system_prompt = "Eres un analista de emergencias. Respondes en JSON."
        user_prompt = f"""Severidad del 1-10:
TÍTULO: {title}
CONTENIDO: {content[:500]}
JSON: {{"severity": número}}"""
        
        result_text = self._call_ai(system_prompt, user_prompt, max_tokens=50)
        result = self._parse_json(result_text)
        return result.get("severity", 5) if result else 5
    
    def validate_relevance(self, title: str, content: str) -> Tuple[bool, Optional[str]]:
        """Valida relevancia de una noticia."""
        result = self.deep_analyze(title, content)
        if result:
            return result.get('is_relevant', False), result.get('exclusion_reason')
        return True, None  # En caso de error, dejar pasar


# ============================================================
# Factory function
# ============================================================

def create_analyzer(provider: str = None, model: str = None) -> AIAnalyzerV2:
    """
    Crea el analizador con la mejor configuración disponible.
    
    Prioridad:
    1. Si OPENAI_API_KEY está configurada → OpenAI
    2. Si ANTHROPIC_API_KEY está configurada → Anthropic
    3. Error si ninguna está disponible
    
    Se puede forzar con variables de entorno:
    - AI_PROVIDER=openai|anthropic
    - AI_MODEL=gpt-4o-mini|claude-sonnet-4-20250514|etc
    """
    provider = provider or os.environ.get('AI_PROVIDER', '').lower()
    model = model or os.environ.get('AI_MODEL', '')
    
    if not provider:
        if os.environ.get('OPENAI_API_KEY'):
            provider = 'openai'
        elif os.environ.get('ANTHROPIC_API_KEY'):
            provider = 'anthropic'
        else:
            raise ValueError(
                "No se encontró API key. Configura OPENAI_API_KEY o ANTHROPIC_API_KEY"
            )
    
    return AIAnalyzerV2(provider=provider, model=model or None)


# ============================================================
# Test
# ============================================================

def test_triage():
    """Prueba el sistema de triage."""
    print("""
╔════════════════════════════════════════╗
║  Test: AI Analyzer v2 - Triage        ║
╚════════════════════════════════════════╝
""")
    
    analyzer = create_analyzer()
    
    # Simular batch de noticias
    test_batch = [
        {"titulo": "Choque múltiple en Av. Lázaro Cárdenas deja 3 heridos en San Pedro",
         "contenido": "Un accidente vehicular en la avenida Lázaro Cárdenas..."},
        {"titulo": "Bad Bunny anuncia nueva gira por Latinoamérica",
         "contenido": "El cantante puertorriqueño anunció fechas..."},
        {"titulo": "Incendio en bodega de Apodaca moviliza a bomberos",
         "contenido": "Una bodega en el municipio de Apodaca se incendió..."},
        {"titulo": "PIB de México crece 2.3% en el tercer trimestre",
         "contenido": "La economía mexicana registró un crecimiento..."},
        {"titulo": "Balacera en Escobedo deja un muerto y 2 heridos",
         "contenido": "Un enfrentamiento armado en el municipio..."},
        {"titulo": "Bloqueo en carretera a Laredo afecta tráfico en García",
         "contenido": "Manifestantes bloquearon la carretera..."},
        {"titulo": "Terremoto de 7.1 sacude Turquía",
         "contenido": "Un fuerte sismo de magnitud 7.1..."},
        {"titulo": "Inundaciones en colonia Independencia por lluvias",
         "contenido": "Las intensas lluvias de esta tarde provocaron..."},
    ]
    
    # Triage
    print("Ejecutando triage...")
    results = analyzer.batch_triage(test_batch)
    
    print(f"\nResultados del triage:")
    print(f"{'='*70}")
    
    for r in results:
        status = "✅ CANDIDATA" if r.is_candidate else "❌ Descartada"
        print(f"  [{r.index}] {status}")
        print(f"      {test_batch[r.index]['titulo'][:60]}...")
        print(f"      Razón: {r.reason}")
        print(f"      Cat: {r.estimated_category} | Sev: {r.estimated_severity} | Ubic: {r.location_hint}")
        print()
    
    # Análisis profundo de la primera candidata
    candidates = [r for r in results if r.is_candidate]
    if candidates:
        first = candidates[0]
        item = test_batch[first.index]
        print(f"\n{'='*70}")
        print(f"Análisis profundo de: {item['titulo'][:60]}...")
        print(f"{'='*70}\n")
        
        analysis = analyzer.deep_analyze(item['titulo'], item['contenido'])
        if analysis:
            print(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_triage()
