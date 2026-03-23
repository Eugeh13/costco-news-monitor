"""
Módulo de análisis inteligente v2.1 - Agente IA con triage temporal inteligente.

CAMBIO PRINCIPAL vs v2.0:
- El triage ahora extrae la HORA DEL EVENTO de cada noticia
- Compara hora del evento vs hora actual para decidir si el impacto sigue activo
- No se basa en la redacción ("hubo" vs "hay") sino en la ventana temporal real
- Ventana de impacto configurable por tipo de evento

Ejemplo:
- "Choque a las 8am" + hora actual 8:30am → ALERTA (30 min, sigue impactando)
- "Choque a las 8am" + hora actual 11am → DESCARTAR (3 horas, ya se limpió)
- "Choque esta madrugada" + hora actual 2pm → DESCARTAR

Arquitectura de 2 pasos:
1. TRIAGE RÁPIDO: Batch de títulos → filtra por relevancia + impacto temporal activo
2. ANÁLISIS PROFUNDO: Solo candidatas con impacto activo → análisis completo
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

import pytz

CENTRAL_TZ = pytz.timezone('America/Chicago')

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


# ============================================================
# Ventanas de impacto por tipo de evento
# ============================================================

IMPACT_WINDOWS = {
    'accidente_vial': 120,       # 2 horas
    'accidente_vial_grave': 180, # 3 horas
    'incendio': 180,             # 3 horas
    'seguridad': 240,            # 4 horas
    'bloqueo': 360,              # 6 horas
    'desastre_natural': 480,     # 8 horas
    'default': 120,              # 2 horas por defecto
}


@dataclass
class TriageResult:
    """Resultado del triage rápido para una noticia."""
    index: int
    is_candidate: bool
    reason: str
    estimated_category: str
    estimated_severity: int
    location_hint: str
    event_time_extracted: str
    estimated_minutes_ago: int
    impact_still_active: bool


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
    Analizador de IA con triage temporal inteligente.
    
    La IA no solo clasifica relevancia, sino que estima CUÁNDO ocurrió
    el evento y si su impacto sigue activo al momento del monitoreo.
    """
    
    def __init__(self, provider: str = "openai", model: Optional[str] = None):
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
            raise ValueError(f"Provider no soportado: {provider}")
        
        print(f"  ✓ AI Analyzer v2.1: {self.provider} / {self.model}")

    # ========================================================
    # Capa de abstracción para llamadas a IA
    # ========================================================
    
    def _call_ai(self, system_prompt: str, user_prompt: str, 
                 max_tokens: int = 1000, temperature: float = 0.1) -> Optional[str]:
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
        if not text:
            return None
        try:
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

    def _get_current_time_str(self) -> str:
        now = datetime.now(CENTRAL_TZ)
        return now.strftime("%H:%M del %d/%m/%Y")

    # ========================================================
    # PASO 1: Triage rápido con análisis temporal
    # ========================================================
    
    def batch_triage(self, news_items: List[dict]) -> List[TriageResult]:
        """
        Filtra un batch de noticias en UNA SOLA llamada.
        
        La IA extrae la hora del evento y estima si el impacto
        sigue activo comparando con la hora actual.
        """
        if not news_items:
            return []
        
        current_time = self._get_current_time_str()
        
        titulares = []
        for i, item in enumerate(news_items):
            titulo = item.get('titulo', '')[:120]
            snippet = item.get('contenido', '')[:80]
            titulares.append(f"{i}: {titulo} | {snippet}")
        
        titulares_text = "\n".join(titulares)
        
        system_prompt = """Eres un filtro para un sistema de ALERTAS EN TIEMPO REAL de emergencias 
en Monterrey, NL. Tu objetivo es identificar eventos que ESTÁN IMPACTANDO LA ZONA EN ESTE MOMENTO.

NO es un resumen de noticias — es un sistema de ALERTA ACTIVA. Solo interesan eventos cuyo 
impacto (vialidad cortada, zona acordonada, peligro activo) sigue presente AHORA MISMO.

Respondes en JSON."""

        user_prompt = f"""HORA ACTUAL: {current_time} (zona horaria: Central/CDT)

Analiza estos {len(news_items)} titulares. Para cada uno:

1. ¿Es un evento de alto impacto en Monterrey? (accidente, incendio, balacera, bloqueo, desastre)
2. ¿CUÁNDO ocurrió? Extrae la hora del evento o estímala con pistas del texto
3. ¿Cuántos MINUTOS han pasado desde el evento hasta la HORA ACTUAL?
4. ¿El impacto en la zona SIGUE ACTIVO ahora? Usa estas ventanas:
   - Accidente vial: impacto ~2 horas después
   - Accidente grave (víctimas fatales, múltiples vehículos): ~3 horas
   - Incendio activo: ~3 horas
   - Balacera/seguridad: ~4 horas
   - Bloqueo/manifestación: ~6 horas
   - Inundación/desastre: ~8 horas

TITULARES:
{titulares_text}

REGLAS CLAVE:
- Si dice "a las 8am" y ahora son las 8:30am → 30 min → impacto ACTIVO (accidente dura ~2h)
- Si dice "a las 8am" y ahora son las 11am → 180 min → impacto NO activo
- Si dice "esta madrugada" y ahora es la tarde → impacto NO activo
- Si dice "ayer", "la semana pasada" → DESCARTAR
- Si dice "hace minutos", "al momento", "se reporta" → impacto ACTIVO
- Si NO puedes determinar la hora pero la noticia parece muy reciente → asumir impacto activo
- Notas de SEGUIMIENTO ("murió la persona atropellada", "identifican a víctima") → DESCARTAR
- Obituarios, recuentos, aniversarios → DESCARTAR

UBICACIÓN (debe ser):
- Monterrey o área metropolitana: San Pedro, San Nicolás, Guadalupe, Apodaca, Santa Catarina, Escobedo, García
- NO otras ciudades ni municipios lejanos

EXCLUIR: espectáculos, deportes, política, economía, farándula

Responde con JSON:
{{
  "results": [
    {{
      "index": 0,
      "is_candidate": true/false,
      "reason": "razón breve (max 20 palabras)",
      "category": "accidente_vial|incendio|seguridad|bloqueo|desastre_natural|no_relevante",
      "severity_estimate": 1-10,
      "location_hint": "ubicación mencionada o 'no_especifica'",
      "event_time": "hora extraída ('08:30', 'hace 20 min', 'esta mañana', 'no_detectada')",
      "minutes_ago": número estimado de minutos desde el evento (-1 si no se puede),
      "impact_active": true/false
    }}
  ]
}}

IMPORTANTE: 
- Incluye TODOS los {len(news_items)} titulares
- is_candidate = true SOLO si: evento de alto impacto + EN Monterrey + impacto SIGUE activo
- Si evento es relevante PERO el impacto ya no está activo → is_candidate = false, reason: "impacto ya no activo (~X horas)"
"""

        result_text = self._call_ai(
            system_prompt, 
            user_prompt, 
            max_tokens=min(5000, len(news_items) * 100),
            temperature=0.1
        )
        
        parsed = self._parse_json(result_text)
        if not parsed or 'results' not in parsed:
            print(f"  ⚠️ Triage falló, marcando todas como candidatas (fallback)")
            return [
                TriageResult(
                    index=i, is_candidate=True, reason="triage_fallback",
                    estimated_category="desconocido", estimated_severity=5,
                    location_hint="no_especifica",
                    event_time_extracted="no_detectada",
                    estimated_minutes_ago=-1,
                    impact_still_active=True
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
                event_time_extracted=item.get('event_time', 'no_detectada'),
                estimated_minutes_ago=item.get('minutes_ago', -1),
                impact_still_active=item.get('impact_active', False),
            ))
        
        candidates = sum(1 for r in triage_results if r.is_candidate)
        relevant_but_old = sum(
            1 for r in triage_results 
            if not r.is_candidate 
            and r.estimated_category != 'no_relevante'
            and 'impacto' in r.reason.lower()
        )
        
        print(f"  🤖 Triage: {candidates}/{len(news_items)} con impacto activo")
        if relevant_but_old > 0:
            print(f"     ({relevant_but_old} eventos relevantes descartados por impacto ya no activo)")
        
        return triage_results

    # ========================================================
    # PASO 2: Análisis profundo (individual)
    # ========================================================
    
    def deep_analyze(self, title: str, content: str) -> Optional[Dict]:
        """
        Análisis profundo con evaluación temporal de impacto.
        """
        current_time = self._get_current_time_str()
        
        system_prompt = """Eres un analista de emergencias en tiempo real para Monterrey, NL.
Tu análisis se usa para ALERTAS ACTIVAS — solo importan eventos cuyo impacto sigue presente.
Respondes en JSON."""

        user_prompt = f"""HORA ACTUAL: {current_time}

Analiza esta noticia:

TÍTULO: {title}
CONTENIDO: {content[:2500]}

Responde con este JSON:
{{
  "is_relevant": true/false,
  "category": "accidente_vial|incendio|seguridad|bloqueo|desastre_natural|no_relevante",
  "severity": 1-10,
  "location": {{
    "extracted": "ubicación exacta (calle, cruce, colonia)",
    "normalized": "para geocodificación (ej: 'Av Lázaro Cárdenas y Fundadores, San Pedro Garza García, NL')",
    "municipality": "municipio",
    "confidence": 0.0-1.0,
    "is_specific": true/false
  }},
  "event_time": {{
    "extracted": "hora del evento como aparece en la noticia",
    "estimated_time": "HH:MM formato 24h",
    "minutes_since_event": minutos desde el evento hasta ahora,
    "impact_still_active": true/false,
    "impact_reasoning": "por qué sí/no sigue activo (1 línea)"
  }},
  "summary": "resumen en max 100 caracteres",
  "details": {{
    "victims": 0,
    "traffic_impact": "none|low|medium|high",
    "emergency_services": true/false,
    "time_reference": "current|recent|past|future",
    "affected_roads": ["vialidades afectadas"]
  }},
  "exclusion_reason": null o "razón si no es relevante o impacto ya no activo"
}}

REGLAS:
- is_relevant = true SOLO si evento de alto impacto Y el impacto SIGUE ACTIVO ahora
- Accidentes: impacto activo ~2h (graves ~3h) | Incendios: ~3h | Seguridad: ~4h | Bloqueos: ~6h
- Notas de seguimiento → is_relevant: false
- severity 1-3: menor | 4-6: moderado | 7-8: grave | 9-10: crítico"""

        result_text = self._call_ai(system_prompt, user_prompt, max_tokens=1000, temperature=0.1)
        result = self._parse_json(result_text)
        
        return result

    # ========================================================
    # Métodos de compatibilidad
    # ========================================================
    
    def analyze_news(self, title: str, content: str) -> Optional[Dict]:
        return self.deep_analyze(title, content)
    
    def extract_location_ai(self, text: str) -> Optional[Dict]:
        system_prompt = "Eres un experto en geografía de Monterrey, NL. Respondes en JSON."
        user_prompt = f"""Extrae la ubicación de esta noticia:

{text[:1000]}

JSON: {{"location": "ubicación exacta", "normalized": "para geocodificar", "confidence": 0-1, "is_specific": true/false}}"""
        
        result_text = self._call_ai(system_prompt, user_prompt, max_tokens=200)
        return self._parse_json(result_text)
    
    def classify_severity(self, title: str, content: str) -> int:
        system_prompt = "Eres un analista de emergencias. Respondes en JSON."
        user_prompt = f"""Severidad del 1-10:
TÍTULO: {title}
CONTENIDO: {content[:500]}
JSON: {{"severity": número}}"""
        
        result_text = self._call_ai(system_prompt, user_prompt, max_tokens=50)
        result = self._parse_json(result_text)
        return result.get("severity", 5) if result else 5
    
    def validate_relevance(self, title: str, content: str) -> Tuple[bool, Optional[str]]:
        result = self.deep_analyze(title, content)
        if result:
            return result.get('is_relevant', False), result.get('exclusion_reason')
        return True, None


# ============================================================
# Factory function
# ============================================================

def create_analyzer(provider: str = None, model: str = None) -> AIAnalyzerV2:
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
    print("""
╔════════════════════════════════════════╗
║  Test: AI Analyzer v2.1 - Temporal    ║
╚════════════════════════════════════════╝
""")
    
    analyzer = create_analyzer()
    now = datetime.now(CENTRAL_TZ)
    print(f"Hora actual: {now.strftime('%H:%M %Z')}\n")
    
    test_batch = [
        {"titulo": "Choque múltiple en Av. Lázaro Cárdenas deja 3 heridos hace 20 minutos",
         "contenido": "Un accidente vehicular en la avenida Lázaro Cárdenas..."},
        {"titulo": "Muere ciclista que fue atropellado ayer en Morones Prieto",
         "contenido": "Falleció en el hospital el ciclista que fue embestido..."},
        {"titulo": "Incendio en bodega de Apodaca, bomberos en el lugar",
         "contenido": "Se reporta incendio activo en bodega..."},
        {"titulo": "Recuento: los 5 accidentes más graves del mes en Monterrey",
         "contenido": "Durante marzo se registraron varios accidentes..."},
        {"titulo": "Balacera esta madrugada en Escobedo deja un muerto",
         "contenido": "Un enfrentamiento armado a las 3am en el municipio..."},
        {"titulo": "Bloqueo activo en carretera a Laredo, manifestantes cierran paso",
         "contenido": "Manifestantes mantienen bloqueada la carretera..."},
    ]
    
    results = analyzer.batch_triage(test_batch)
    
    print(f"\nResultados:")
    print(f"{'='*70}")
    
    for r in results:
        status = "✅ ALERTA ACTIVA" if r.is_candidate else "❌ Descartada"
        print(f"  [{r.index}] {status}")
        print(f"      {test_batch[r.index]['titulo'][:60]}...")
        print(f"      Razón: {r.reason}")
        print(f"      Hora evento: {r.event_time_extracted} | ~{r.estimated_minutes_ago} min ago")
        print(f"      Impacto activo: {'SÍ' if r.impact_still_active else 'NO'}")
        print()


if __name__ == "__main__":
    test_triage()
