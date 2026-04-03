# Sistema de Monitoreo de Noticias — Costco Monterrey

Sistema automatizado de monitoreo de noticias de alto impacto (accidentes, incendios, balaceras, bloqueos) cerca de sucursales Costco en Monterrey, NL.

**Versión**: 2.1 — Multi-source + Triage IA
**IA**: OpenAI GPT-4o-mini o Anthropic Claude (configurable)

---

## Características

- **Scraping multi-fuente**: Google News RSS + GNews + RSS directo (Milenio, Info7) + Crawl4AI
- **Triage IA en batch**: 1 llamada clasifica ~50 noticias → ~70% menos costo vs v1
- **Análisis profundo**: Solo candidatas reciben análisis completo (artículo completo + IA)
- **Agente operacional**: La IA razona como gerente de operaciones, no como clasificador
- **Filtro temporal**: Solo noticias de la última hora
- **Radio de monitoreo**: 5 km alrededor de cada Costco + detección por vialidades clave
- **Detección de duplicados**: Hash SHA-256 + PostgreSQL (ventana 24h)
- **Alertas Telegram**: En tiempo real con severidad 1-10 e impacto operacional
- **Ejecución automática**: Cada 30 minutos en horarios fijos (:00 y :30), zona CST

---

## Ubicaciones Monitoreadas

| Sucursal | Coordenadas | Radio |
|----------|-------------|-------|
| Costco Carretera Nacional | 25.5781, -100.2512 | 5 km |
| Costco Cumbres | 25.7296, -100.3928 | 5 km |
| Costco Valle Oriente | 25.6397, -100.3176 | 5 km |

---

## Eventos Monitoreados

- **Accidentes viales**: Choques, volcaduras, atropellos
- **Incendios**: Edificios, locales, vehículos
- **Seguridad**: Balaceras, enfrentamientos
- **Bloqueos**: Manifestaciones, cierres viales
- **Desastres naturales**: Inundaciones, trombas

---

## Arquitectura del Pipeline

```
FUENTES
  Google News RSS  ──┐
  GNews API        ──┼──► scraper_v3.py ──► NewsItem[]
  RSS directo      ──┤
  Crawl4AI         ──┘
        │
        ▼
FILTROS
  ⏰ Tiempo (última hora) ── time_filter.py
  🔄 Duplicados (DB + local) ── database.py / storage.py
        │
        ▼
TRIAGE IA (batch)
  ai_analyzer_v2.py  ──► 1 llamada para ~50 noticias
  Candidatas: ~5-10% del total
        │
        ▼
ANÁLISIS PROFUNDO (solo candidatas)
  Crawl4AI extrae artículo completo
  IA analiza impacto operacional por tienda
        │
        ▼
GEOCODIFICACIÓN
  geolocation.py + Nominatim
  Verificación radio 5 km + vialidades clave
        │
        ▼
SALIDA
  📱 Telegram (notifier_ai.py)
  💾 PostgreSQL (database.py)
```

---

## Estructura del Proyecto

```
├── main_ai_v2.py           # Script principal — orquesta el pipeline
├── run_scheduled_v2.py     # Ejecutor programado (cada 30 min)
├── scraper_v3.py           # Scraping multi-fuente
├── ai_analyzer_v2.py       # Triage batch + análisis profundo (OpenAI/Anthropic)
├── config.py               # Coordenadas Costco, keywords, radio
├── time_filter.py          # Filtro temporal (última hora)
├── geolocation.py          # Geocodificación y cálculo de distancias
├── analyzer.py             # Pre-filtro por palabras clave
├── notifier_ai.py          # Notificaciones a Telegram
├── database.py             # Gestión PostgreSQL
├── storage.py              # Cache local de URLs procesadas
├── database_schema.sql     # Schema de la tabla noticias
├── requirements.txt        # Dependencias Python
├── Procfile                # Entrada Railway: run_scheduled_v2.py
└── runtime.txt             # Python 3.11
```

---

## Instalación y Configuración

### Requisitos

- Python 3.11+
- Clave de API OpenAI **o** Anthropic
- Bot de Telegram
- PostgreSQL (Railway o local)

### Variables de Entorno

```env
# IA — usar uno de los dos
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# PostgreSQL
DATABASE_URL=postgresql://user:password@host:5432/database
```

### Instalación local

```bash
git clone https://github.com/Eugeh13/costco-news-monitor.git
cd costco-news-monitor
pip install -r requirements.txt

# Crear tabla en PostgreSQL
psql $DATABASE_URL -f database_schema.sql

# Ejecutar una vez (prueba)
python3.11 main_ai_v2.py

# Ejecutar programado (cada 30 minutos)
python3.11 run_scheduled_v2.py
```

### Despliegue en Railway

1. Conectar repositorio GitHub en Railway
2. Configurar las variables de entorno
3. Railway detecta el `Procfile` y ejecuta `run_scheduled_v2.py` automáticamente

---

## Despliegue en Railway

### Paso 1: Crear proyecto

1. Ve a [Railway.app](https://railway.app/)
2. "Start a New Project" → "Deploy from GitHub repo"
3. Selecciona este repositorio

### Paso 2: Agregar PostgreSQL

1. En el proyecto, click en "+ New" → "Database" → "PostgreSQL"
2. Copia el valor de `DATABASE_URL` de las variables generadas

### Paso 3: Configurar Variables

En la pestaña "Variables" del servicio web, agrega:

```
OPENAI_API_KEY=...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
DATABASE_URL=...   (copiado del paso 2)
```

### Paso 4: Crear tabla

Ejecuta `database_schema.sql` en la consola de PostgreSQL de Railway.

---

## Costos Estimados

### IA (OpenAI gpt-4o-mini)
- **Por día**: ~$0.05–0.15 USD (triage batch reduce ~70% vs v1)
- **Por mes**: ~$1.50–5 USD

### Railway
- **Hobby Plan**: $5 USD/mes (incluye PostgreSQL)

**Total estimado**: $6–10 USD/mes

---

## Ejemplo de Alerta Telegram

```
🚨 ALERTA COSTCO MTY

📍 Accidente Vial
📰 Choque múltiple en Lázaro Cárdenas deja 3 heridos

⚡ Severidad: GRAVE (7/10)
👥 Víctimas/Heridos: 3
🚗 Impacto en tráfico: ALTO
🚑 Servicios de emergencia en el lugar

📏 A 2.1 km de Costco Valle Oriente
🗺️ Av. Lázaro Cárdenas altura Fundadores

📝 Accidente vehicular con tres personas lesionadas.
   Impacto operacional: clientes de Valle Oriente
   con dificultad de acceso por Lázaro Cárdenas.

📡 Milenio Monterrey
🔗 [Ver noticia completa]

⏰ 03/04/2026 18:00 CST
```

---

## Configuración Avanzada

### Cambiar proveedor de IA

La función `create_analyzer()` en `ai_analyzer_v2.py` detecta automáticamente qué clave está disponible. Para forzar uno:

```python
# En main_ai_v2.py
from ai_analyzer_v2 import AIAnalyzerV2
self.ai = AIAnalyzerV2(provider="anthropic")  # o "openai"
```

### Cambiar ventana de tiempo

En `main_ai_v2.py`, línea del `TimeFilter`:
```python
self.time_filter = TimeFilter(max_age_hours=1)   # default: 1 hora
self.time_filter = TimeFilter(max_age_hours=0.5) # 30 minutos
```

### Cambiar radio de monitoreo

En `config.py`:
```python
RADIUS_KM = 5.0  # kilómetros alrededor de cada Costco
```

---

## Documentación Adicional

| Archivo | Contenido |
|---------|-----------|
| `GUIA_CONFIGURACION_POSTGRESQL_RAILWAY.md` | Setup detallado de la base de datos |
| `FILTRO_TIEMPO_IMPLEMENTADO.md` | Explicación del filtro temporal |
| `EXPLICACION_CRITERIOS_BUSQUEDA.md` | Criterios de búsqueda y palabras clave |
| `GUIA_MEJORAS_IA.md` | Historial de mejoras del módulo IA |
| `README_COMPLETO.md` | Documentación técnica completa v2.0 |

---

## Pruebas

```bash
# Probar pipeline completo (una ejecución)
python3.11 main_ai_v2.py

# Probar scraper
python3.11 scraper_v3.py

# Probar filtro de tiempo
python3.11 time_filter.py

# Probar notificador
python3.11 notifier_ai.py test
```

---

## Seguridad

- Credenciales exclusivamente en variables de entorno
- No hay API keys en el código fuente
- `.gitignore` configurado para archivos sensibles

---

**Uso privado — Costco Monterrey**
