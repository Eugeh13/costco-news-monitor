"""
Agente de Inteligencia Operacional para Costco Monterrey v3.0

Este NO es un clasificador de noticias. Es un AGENTE que razona como un 
gerente de operaciones de Costco. Lee una noticia y piensa:

1. ¿Esto está pasando AHORA MISMO?
2. ¿Afecta a alguna de mis tiendas? ¿Cómo?
   - ¿Clientes no pueden llegar? (vialidad bloqueada)
   - ¿Empleados en riesgo? (balacera cerca)
   - ¿La tienda debe cerrar o evacuar? (incendio, inundación)
   - ¿Proveedores/camiones no pueden entregar? (bloqueo en ruta)
3. ¿Qué acción debe tomar Costco?

Arquitectura:
- TRIAGE: La IA recibe la hora actual + las 3 ubicaciones Costco + las noticias
  y razona sobre cuáles tienen impacto operacional ACTIVO
- ANÁLISIS PROFUNDO: Para candidatas, genera un reporte de inteligencia
  con impacto específico por tienda y acciones recomendadas
"""

import os
import json
from datetime import datetime
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

import pytz

CENTRAL_TZ = pytz.timezone('America/Chicago')

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


# ============================================================
# Contexto operacional de Costco Monterrey
# ============================================================

COSTCO_CONTEXT = """
TIENDAS COSTCO EN MONTERREY (tu responsabilidad):

1. COSTCO CARRETERA NACIONAL
   - Dirección: Carretera Nacional Km. 268, Col. La Estanzuela
   - Vialidades clave: Carretera Nacional, Av. Alfonso Reyes, Av. Revolución
   - Zona: Sur de Monterrey, camino a Santiago
   - Riesgo principal: Accidentes en carretera, crecidas de río

2. COSTCO CUMBRES
   - Dirección: Alejandro de Rodas 6767, Cumbres
   - Vialidades clave: Av. Alejandro de Rodas, Av. Lincoln, Paseo de los Leones
   - Zona: Noroeste de Monterrey
   - Riesgo principal: Tráfico pesado, bloqueos en Lincoln

3. COSTCO VALLE ORIENTE
   - Dirección: Av. Lázaro Cárdenas 800, San Pedro Garza García
   - Vialidades clave: Av. Lázaro Cárdenas, Av. Vasconcelos, Av. Morones Prieto, Constitución
   - Zona: San Pedro, zona de alto tráfico
   - Riesgo principal: Accidentes en Lázaro Cárdenas, eventos en zona de hospitales

RADIO DE MONITOREO: 3 km alrededor de cada tienda.

TIPOS DE IMPACTO OPERACIONAL:
- ACCESO CLIENTES: Vialidad principal bloqueada → clientes no pueden llegar
- SEGURIDAD PERSONAS: Balacera/incendio cerca → riesgo para empleados y clientes
- EVACUACIÓN: Amenaza directa a la tienda → cerrar y evacuar
- CADENA SUMINISTRO: Bloqueo en ruta de proveedores → afecta entregas
- REPUTACIONAL: Evento grave muy cerca → percepción de inseguridad en la zona
"""


@dataclass
class TriageResult:
    """Resultado del triage del agente."""
    index: int
    is_candidate: bool
    reason: str
    estimated_category: str
    estimated_severity: int
    location_hint: str
    event_time_extracted: str
    estimated_minutes_ago: int
    impact_still_active: bool
    costco_affected: str          # "carretera_nacional", "cumbres", "valle_oriente", "ninguno", "multiples"
    operational_impact_type: str   # "acceso_clientes", "seguridad_personas", "evacuacion", "cadena_suministro", "ninguno"


class AIAnalyzerV2:
    """
    Agente de Inteligencia Operacional para Costco Monterrey.
    
    Piensa como un gerente de operaciones que necesita decidir
    en tiempo real si una situación requiere acción.
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
        
        print(f"  ✓ Agente Costco Intel v3.0: {self.provider} / {self.model}")

    # ========================================================
    # Llamada a IA
    # ========================================================
    
    def _call_ai(self, system_prompt: str, user_prompt: str, 
                 max_tokens: int = 1000, temperature: float = 0.15) -> Optional[str]:
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
                    system=system_prompt + "\n\nResponde SOLO con JSON válido.",
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=temperature,
                )
                return response.content[0].text
                
        except Exception as e:
            print(f"  ⚠️ Error IA ({self.provider}): {e}")
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
            print(f"  ⚠️ JSON parse error: {e}")
            return None

    def _get_current_time_str(self) -> str:
        now = datetime.now(CENTRAL_TZ)
        return now.strftime("%H:%M del %A %d/%m/%Y")

    # ========================================================
    # TRIAGE: El agente evalúa impacto operacional
    # ========================================================
    
    def batch_triage(self, news_items: List[dict]) -> List[TriageResult]:
        """
        El agente recibe un batch de noticias y razona:
        - ¿Está pasando ahora?
        - ¿Afecta a algún Costco?
        - ¿Qué tipo de impacto operacional tiene?
        - ¿Costco necesita actuar?
        """
        if not news_items:
            return []
        
        current_time = self._get_current_time_str()
        
        titulares = []
        for i, item in enumerate(news_items):
            titulo = item.get('titulo', '')[:130]
            snippet = item.get('contenido', '')[:100]
            titulares.append(f"{i}: {titulo} | {snippet}")
        
        titulares_text = "\n".join(titulares)
        
        system_prompt = f"""Eres el agente de inteligencia operacional de Costco Monterrey. 
Tu trabajo es monitorear noticias en tiempo real y determinar cuáles representan 
una AMENAZA ACTIVA para las operaciones de las tiendas Costco.

{COSTCO_CONTEXT}

Piensas como un gerente de operaciones: "¿Esto afecta a mi tienda AHORA MISMO? 
¿Mis clientes pueden llegar? ¿Mis empleados están seguros? ¿Necesito hacer algo?"

Respondes en JSON."""

        user_prompt = f"""HORA ACTUAL: {current_time} (CDT - Monterrey)

Evalúa estos {len(news_items)} titulares como agente de inteligencia de Costco.

Para cada noticia, razona:
1. ¿Es un evento de emergencia? (accidente, incendio, balacera, bloqueo, inundación)
2. ¿Está en Monterrey/área metropolitana? ¿Cerca de algún Costco?
3. ¿CUÁNDO ocurrió? Extrae la hora o estímala
4. ¿El impacto SIGUE ACTIVO ahora? (no sirve un choque de hace 5 horas)
5. ¿Cómo afecta a Costco específicamente?

TITULARES:
{titulares_text}

VENTANAS DE IMPACTO ACTIVO:
- Accidente vial simple: ~2 horas después del evento
- Accidente grave (víctimas, múltiples vehículos): ~3 horas
- Incendio: ~3 horas (zona acordonada, humo)
- Balacera/enfrentamiento: ~4 horas (zona acordonada, presencia militar)
- Bloqueo/manifestación: hasta que se levante (puede ser todo el día)
- Inundación: ~8 horas

DESCARTA INMEDIATAMENTE:
- Noticias de OTRAS CIUDADES (CDMX, Guadalajara, Torreón, Durango, etc.)
- Municipios lejanos de NL (Linares, Santiago, Cadereyta, Pesquería)
- Notas de SEGUIMIENTO ("murió el herido de ayer", "identifican a víctima")
- Recuentos, estadísticas, aniversarios, opinión
- Deportes, espectáculos, política, farándula, economía general
- Eventos FUTUROS ("mañana habrá cierre vial por evento")

Responde con JSON:
{{
  "results": [
    {{
      "index": 0,
      "is_candidate": true/false,
      "reason": "razonamiento breve desde perspectiva Costco (max 25 palabras)",
      "category": "accidente_vial|incendio|seguridad|bloqueo|desastre_natural|no_relevante",
      "severity_estimate": 1-10,
      "location_hint": "ubicación del evento",
      "event_time": "hora extraída o estimada del evento",
      "minutes_ago": minutos desde el evento (-1 si no se puede determinar),
      "impact_active": true/false,
      "costco_affected": "carretera_nacional|cumbres|valle_oriente|multiples|ninguno",
      "operational_impact": "acceso_clientes|seguridad_personas|evacuacion|cadena_suministro|ninguno"
    }}
  ]
}}

RECUERDA: is_candidate = true SOLO si:
✓ Evento de emergencia real
✓ En Monterrey / área metropolitana  
✓ El impacto SIGUE ACTIVO en este momento
✓ Afecta o podría afectar operaciones de al menos un Costco
"""

        result_text = self._call_ai(
            system_prompt, 
            user_prompt, 
            max_tokens=min(6000, len(news_items) * 120),
            temperature=0.15
        )
        
        parsed = self._parse_json(result_text)
        if not parsed or 'results' not in parsed:
            print(f"  ⚠️ Triage falló — fallback: todas como candidatas")
            return [
                TriageResult(
                    index=i, is_candidate=True, reason="triage_fallback",
                    estimated_category="desconocido", estimated_severity=5,
                    location_hint="no_especifica",
                    event_time_extracted="no_detectada",
                    estimated_minutes_ago=-1,
                    impact_still_active=True,
                    costco_affected="ninguno",
                    operational_impact_type="ninguno"
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
                costco_affected=item.get('costco_affected', 'ninguno'),
                operational_impact_type=item.get('operational_impact', 'ninguno'),
            ))
        
        candidates = sum(1 for r in triage_results if r.is_candidate)
        relevant_expired = sum(
            1 for r in triage_results 
            if not r.is_candidate and r.estimated_category != 'no_relevante'
        )
        
        print(f"  🤖 Triage: {candidates}/{len(news_items)} amenazas activas para Costco")
        if relevant_expired > 0:
            print(f"     ({relevant_expired} eventos descartados: impacto expirado, otra ciudad, o seguimiento)")
        
        return triage_results

    # ========================================================
    # ANÁLISIS PROFUNDO: Reporte de inteligencia para Costco
    # ========================================================
    
    def deep_analyze(self, title: str, content: str) -> Optional[Dict]:
        """
        Genera un reporte de inteligencia operacional para Costco.
        
        No es solo "¿qué pasó?" sino "¿qué significa para Costco 
        y qué debemos hacer?"
        """
        current_time = self._get_current_time_str()
        
        system_prompt = f"""Eres el analista de inteligencia operacional de Costco Monterrey.
Generas reportes de situación para que los gerentes de tienda tomen decisiones.

{COSTCO_CONTEXT}

Tu reporte debe responder: ¿Qué pasó? ¿Dónde? ¿Sigue activo? ¿Qué Costco se afecta? ¿Qué hacer?

Respondes en JSON."""

        user_prompt = f"""HORA ACTUAL: {current_time}

Genera reporte de inteligencia para este evento:

TÍTULO: {title}
CONTENIDO: {content[:3000]}

JSON requerido:
{{
  "is_relevant": true/false,
  "category": "accidente_vial|incendio|seguridad|bloqueo|desastre_natural|no_relevante",
  "severity": 1-10,
  
  "location": {{
    "extracted": "ubicación exacta del evento",
    "normalized": "dirección completa para geocodificar",
    "municipality": "municipio",
    "confidence": 0.0-1.0,
    "is_specific": true/false,
    "nearby_landmarks": "referencia conocida cercana"
  }},
  
  "temporal": {{
    "event_time": "hora del evento (HH:MM o descripción)",
    "minutes_since_event": número,
    "impact_still_active": true/false,
    "estimated_duration_remaining": "tiempo estimado que seguirá el impacto",
    "reasoning": "por qué sí/no sigue activo"
  }},
  
  "costco_impact": {{
    "affected_store": "carretera_nacional|cumbres|valle_oriente|multiples|ninguno",
    "impact_type": "acceso_clientes|seguridad_personas|evacuacion|cadena_suministro|ninguno",
    "impact_level": "critico|alto|medio|bajo|ninguno",
    "affected_roads": ["vialidades afectadas que usan clientes/proveedores de Costco"],
    "customer_access_blocked": true/false,
    "employee_safety_risk": true/false,
    "supply_chain_affected": true/false
  }},
  
  "recommended_actions": [
    "acción específica que Costco debería tomar"
  ],
  
  "summary": "resumen ejecutivo en max 120 caracteres",
  
  "details": {{
    "victims": 0,
    "traffic_impact": "none|low|medium|high",
    "emergency_services": true/false,
    "time_reference": "current|recent|past|future",
    "affected_roads": ["lista completa de vialidades mencionadas"]
  }},
  
  "exclusion_reason": null o "razón de exclusión"
}}

REGLAS:
- is_relevant = true SOLO si hay impacto operacional ACTIVO para Costco
- recommended_actions: sé específico (ej: "Alertar personal de Costco Valle Oriente", 
  "Recomendar ruta alterna por Vasconcelos", "Monitorear evolución del incendio")
- Si el evento es grave pero lejos de cualquier Costco (>3km) → is_relevant: false
- Si el impacto ya expiró → is_relevant: false
- severity: desde perspectiva de impacto en Costco, no solo gravedad del evento"""

        result_text = self._call_ai(system_prompt, user_prompt, max_tokens=1200, temperature=0.15)
        return self._parse_json(result_text)

    # ========================================================
    # Compatibilidad con sistema existente
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
        user_prompt = f"""Severidad del 1-10 para operaciones Costco:
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
# Factory
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
            raise ValueError("Configura OPENAI_API_KEY o ANTHROPIC_API_KEY")
    
    return AIAnalyzerV2(provider=provider, model=model or None)


# ============================================================
# Test
# ============================================================

def test_agent():
    print("""
╔═══════════════════════════════════════════════╗
║  Test: Agente Intel Costco v3.0              ║
╚═══════════════════════════════════════════════╝
""")
    
    analyzer = create_analyzer()
    now = datetime.now(CENTRAL_TZ)
    print(f"Hora actual: {now.strftime('%H:%M %Z')}\n")
    
    test_batch = [
        {"titulo": "Choque múltiple en Lázaro Cárdenas cierra 2 carriles, hace 20 minutos",
         "contenido": "Accidente en Av Lázaro Cárdenas altura de Fundadores deja 3 heridos, tráfico detenido"},
        {"titulo": "Muere ciclista que fue atropellado ayer en Morones Prieto",
         "contenido": "Falleció en hospital el ciclista embestido ayer por la tarde"},
        {"titulo": "Incendio activo en bodega sobre Lincoln, bomberos en el lugar",
         "contenido": "Se reporta fuego en bodega industrial, columna de humo visible desde Cumbres"},
        {"titulo": "Bad Bunny anuncia concierto en Monterrey para julio",
         "contenido": "El cantante confirmó fecha en el Estadio BBVA"},
        {"titulo": "Balacera en Escobedo hace 30 minutos, zona acordonada",
         "contenido": "Enfrentamiento en colonia Pedregal, presencia de Fuerza Civil"},
        {"titulo": "Bloqueo en Carretera Nacional por manifestantes, tráfico detenido",
         "contenido": "Manifestantes cierran paso a altura de La Estanzuela desde hace 1 hora"},
        {"titulo": "Inundación en Constitución y Morones Prieto por lluvias intensas",
         "contenido": "Nivel del agua sube, vehículos varados, Protección Civil en la zona"},
        {"titulo": "PIB de Nuevo León creció 3.5% en el último trimestre",
         "contenido": "La economía del estado muestra signos positivos"},
    ]
    
    results = analyzer.batch_triage(test_batch)
    
    print(f"\n{'='*70}")
    for r in results:
        status = "🚨 AMENAZA ACTIVA" if r.is_candidate else "⬜ No relevante"
        print(f"\n  [{r.index}] {status}")
        print(f"      {test_batch[r.index]['titulo'][:65]}...")
        print(f"      Razón: {r.reason}")
        if r.is_candidate:
            print(f"      Costco afectado: {r.costco_affected}")
            print(f"      Impacto: {r.operational_impact_type}")
            print(f"      Hora evento: {r.event_time_extracted} | ~{r.estimated_minutes_ago} min")
    
    # Análisis profundo de primera candidata
    candidates = [r for r in results if r.is_candidate]
    if candidates:
        first = candidates[0]
        item = test_batch[first.index]
        print(f"\n\n{'='*70}")
        print(f"REPORTE DE INTELIGENCIA: {item['titulo'][:50]}...")
        print(f"{'='*70}")
        analysis = analyzer.deep_analyze(item['titulo'], item['contenido'])
        if analysis:
            print(json.dumps(analysis, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    test_agent()
