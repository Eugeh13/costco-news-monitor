# 🚨 Sistema de Monitoreo de Noticias - Costco Monterrey

Sistema automatizado de monitoreo de noticias de alto impacto para 3 ubicaciones de Costco en Monterrey, México. Utiliza **análisis de IA con OpenAI**, scraping de portales de noticias, monitoreo de Twitter/X, y **base de datos PostgreSQL** para detección de duplicados y tracking histórico.

---

## 🎯 Características Principales

### ✅ Monitoreo Inteligente
- **Análisis con IA (OpenAI GPT-4o-mini):** Clasificación automática de severidad, extracción de ubicaciones, detección de víctimas e impacto en tráfico
- **Múltiples fuentes:** Portales de noticias (Milenio, El Horizonte) + Twitter/X (10 cuentas locales)
- **Filtro temporal:** Solo noticias de última hora (máximo 1 hora de antigüedad)
- **Zona horaria:** CST (Hora Central) configurada con pytz

### 🗄️ Base de Datos PostgreSQL
- **Detección de duplicados:** Evita alertas repetidas del mismo evento entre diferentes fuentes
- **Tracking completo:** Guarda todas las noticias procesadas con información enriquecida
- **Hash de contenido:** Sistema inteligente para identificar noticias duplicadas
- **Preparado para dashboards:** Estructura optimizada para análisis y visualizaciones

### 📍 Geolocalización Precisa
- **3 ubicaciones Costco monitoreadas:**
  - Costco Carretera Nacional (25.6794, -100.2589)
  - Costco Cumbres (25.6522, -100.2893)
  - Costco Valle Oriente (25.6519, -100.3628)
- **Radio de 3 km** alrededor de cada ubicación
- **Vialidades clave:** Detección adicional por nombres de calles importantes

### 🔔 Alertas a Telegram
- Notificaciones enriquecidas con análisis de IA
- Información de severidad (1-10)
- Detalles de ubicación, distancia y Costco afectado
- Enlaces directos a las noticias originales

### ⏰ Ejecución Programada
- Monitoreo cada **30 minutos** en horarios fijos (:00 y :30)
- Desplegado en **Railway** con ejecución automática
- Integración continua con **GitHub**

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                     FUENTES DE NOTICIAS                         │
├─────────────────────────────────────────────────────────────────┤
│  📰 Portales Web          │  🐦 Twitter/X (twscrape)            │
│  - Milenio Última Hora    │  - @pc_mty                          │
│  - Milenio Monterrey      │  - @QueSucedeEnMty                  │
│  - El Horizonte           │  - @vialhermes                      │
│                           │  - ... (10 cuentas)                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESAMIENTO                                │
├─────────────────────────────────────────────────────────────────┤
│  1. ⏰ Filtro Temporal (time_filter.py)                         │
│     └─ Solo noticias de última hora                            │
│                                                                 │
│  2. 🔍 Pre-filtrado (analyzer.py)                              │
│     └─ Palabras clave de alto impacto                          │
│                                                                 │
│  3. 🤖 Análisis con IA (ai_analyzer.py)                        │
│     └─ OpenAI GPT-4o-mini                                      │
│     └─ Severidad, ubicación, víctimas, impacto                 │
│                                                                 │
│  4. 🗺️ Geolocalización (geolocation.py)                        │
│     └─ Nominatim (OpenStreetMap)                               │
│     └─ Cálculo de distancias                                   │
│                                                                 │
│  5. 🗄️ Base de Datos (database.py)                             │
│     └─ PostgreSQL en Railway                                   │
│     └─ Detección de duplicados (hash)                          │
│     └─ Guardado de todas las noticias                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    SALIDA                                       │
├─────────────────────────────────────────────────────────────────┤
│  📱 Telegram (notifier_ai.py)                                   │
│     └─ Alertas enriquecidas con IA                             │
│                                                                 │
│  💾 PostgreSQL                                                  │
│     └─ Registro histórico completo                             │
│     └─ Base para dashboards futuros                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Estructura del Proyecto

```
news_monitor_app/
├── main_ai.py                    # Script principal con análisis de IA
├── run_scheduled_ai.py           # Ejecutor programado (cada 30 min)
├── config.py                     # Configuración de ubicaciones y fuentes
├── config.json                   # Datos de Costcos (coordenadas, vialidades)
│
├── analyzer.py                   # Análisis tradicional (pre-filtrado)
├── ai_analyzer.py                # Análisis con OpenAI (IA)
├── time_filter.py                # Filtro temporal (última hora)
├── geolocation.py                # Geocodificación y cálculo de distancias
├── scraper.py                    # Scraping de portales web
├── twitter_scraper_auth.py       # Scraping de Twitter con twscrape
├── notifier_ai.py                # Notificaciones a Telegram
├── storage.py                    # Almacenamiento local (cache)
├── database.py                   # ⭐ Gestión de PostgreSQL
│
├── database_schema.sql           # ⭐ Schema de la tabla de noticias
├── requirements.txt              # Dependencias Python
├── Procfile                      # Configuración Railway
├── runtime.txt                   # Versión de Python
│
├── GUIA_CONFIGURACION_POSTGRESQL_RAILWAY.md  # ⭐ Guía de setup DB
└── README_COMPLETO.md            # Este archivo
```

---

## 🚀 Instalación y Configuración

### 1. Clonar el Repositorio

```bash
git clone https://github.com/Eugeh13/costco-news-monitor.git
cd costco-news-monitor
```

### 2. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

Crea un archivo `.env` o configura en Railway:

```env
# OpenAI (requerido para análisis de IA)
OPENAI_API_KEY=sk-...

# Telegram (requerido para notificaciones)
TELEGRAM_BOT_TOKEN=7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0
TELEGRAM_CHAT_ID=7510716093

# Twitter (opcional, para monitoreo de Twitter/X)
TWITTER_AUTH_TOKEN=...
TWITTER_CT0=...

# PostgreSQL (requerido para base de datos)
DATABASE_URL=postgresql://user:password@host:5432/database
```

### 4. Configurar PostgreSQL en Railway

Sigue la guía detallada en: **`GUIA_CONFIGURACION_POSTGRESQL_RAILWAY.md`**

Pasos resumidos:
1. Crear servicio PostgreSQL en Railway
2. Copiar `DATABASE_URL` a variables de entorno
3. Ejecutar script `database_schema.sql` para crear tabla
4. Verificar conexión en logs

### 5. Ejecutar Localmente (Pruebas)

```bash
# Ejecutar una vez
python main_ai.py

# Ejecutar programado (cada 30 minutos)
python run_scheduled_ai.py
```

### 6. Desplegar en Railway

1. Conecta tu repositorio de GitHub a Railway
2. Railway detectará automáticamente el `Procfile`
3. Configura las variables de entorno
4. El sistema se ejecutará automáticamente

---

## 🗄️ Base de Datos PostgreSQL

### Tabla: `noticias`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | SERIAL | ID único autoincremental |
| `titulo` | VARCHAR(500) | Título de la noticia |
| `tipo_evento` | VARCHAR(100) | Categoría del evento |
| `fecha_hora` | TIMESTAMP | Fecha y hora del evento |
| `url` | VARCHAR(1000) | URL de la noticia |
| `descripcion` | TEXT | Descripción/resumen |
| `costco_impactado` | VARCHAR(100) | Costco más cercano |
| `fuente` | VARCHAR(100) | Fuente de la noticia |
| `severidad` | INTEGER | Nivel 1-10 (IA) |
| `ubicacion_extraida` | VARCHAR(500) | Ubicación del texto |
| `latitud` | DECIMAL(10,8) | Coordenada latitud |
| `longitud` | DECIMAL(11,8) | Coordenada longitud |
| `distancia_km` | DECIMAL(5,2) | Distancia al Costco |
| `victimas` | INTEGER | Número de víctimas (IA) |
| `impacto_trafico` | VARCHAR(50) | Impacto en tráfico (IA) |
| `servicios_emergencia` | BOOLEAN | Servicios presentes |
| `hash_contenido` | VARCHAR(64) | Hash para duplicados |
| `created_at` | TIMESTAMP | Fecha de creación |

### Detección de Duplicados

El sistema genera un **hash SHA-256** del contenido normalizado:
- Normaliza título + descripción (minúsculas, sin acentos, sin puntuación)
- Genera hash único
- Verifica si existe en las últimas 24 horas
- Si existe → descarta como duplicado
- Si no existe → procesa y guarda

### Consultas Útiles

```sql
-- Ver noticias recientes
SELECT titulo, tipo_evento, severidad, costco_impactado, fecha_hora
FROM noticias
ORDER BY fecha_hora DESC
LIMIT 20;

-- Estadísticas por Costco
SELECT costco_impactado, COUNT(*) as total, AVG(severidad) as severidad_promedio
FROM noticias
GROUP BY costco_impactado;

-- Noticias de alta severidad
SELECT titulo, severidad, costco_impactado, fecha_hora
FROM noticias
WHERE severidad >= 7
ORDER BY severidad DESC;

-- Detectar duplicados
SELECT hash_contenido, COUNT(*) as veces
FROM noticias
GROUP BY hash_contenido
HAVING COUNT(*) > 1;
```

---

## 🔧 Tecnologías Utilizadas

### Backend
- **Python 3.11**
- **OpenAI API** (gpt-4o-mini) - Análisis de IA
- **PostgreSQL** - Base de datos
- **psycopg2** - Driver PostgreSQL

### Scraping
- **BeautifulSoup4** - Parsing HTML
- **Requests** - HTTP requests
- **twscrape** - Twitter/X scraping con autenticación

### Geolocalización
- **geopy** - Geocodificación (Nominatim/OpenStreetMap)
- **Haversine** - Cálculo de distancias

### Notificaciones
- **python-telegram-bot** - Bot de Telegram

### Utilidades
- **pytz** - Zona horaria CST
- **schedule** - Ejecución programada
- **hashlib** - Generación de hashes para duplicados

### Despliegue
- **Railway** - Hosting y PostgreSQL
- **GitHub** - Control de versiones
- **Git** - Integración continua

---

## 📊 Categorías de Eventos Monitoreados

1. **🚗 Accidentes Viales**
   - Choques
   - Volcaduras
   - Atropellamientos
   - Accidentes múltiples

2. **🔥 Incendios**
   - Incendios estructurales
   - Incendios vehiculares
   - Explosiones

3. **🚨 Seguridad**
   - Balaceras
   - Enfrentamientos
   - Robos violentos
   - Persecuciones

4. **🚧 Bloqueos/Manifestaciones**
   - Bloqueos de vialidades
   - Manifestaciones
   - Cierres de carreteras

5. **🌪️ Desastres Naturales**
   - Inundaciones
   - Tormentas severas
   - Deslaves

---

## 📱 Formato de Alertas en Telegram

```
🚨 ALERTA DE ALTO IMPACTO

📋 Categoría: Accidente Vial
⚡ Severidad: 8/10

📰 Título:
Choque múltiple en Carretera Nacional deja 3 heridos

📍 Ubicación:
Carretera Nacional km 267

🏪 Costco Cercano:
Costco Carretera Nacional
📍 Av. Eugenio Garza Sada 3551
📏 Distancia: 1.2 km

👥 Víctimas: 3
🚦 Impacto en Tráfico: Alto
🚑 Servicios de Emergencia: Presentes

📄 Resumen:
Accidente vehicular múltiple en Carretera Nacional...

🔗 Fuente: Milenio Última Hora
🌐 URL: https://...

⏰ 10/11/2025 14:30 CST
```

---

## 🔍 Flujo de Procesamiento

1. **Recolección** (cada 30 minutos)
   - Scraping de ~30 noticias de portales
   - Scraping de ~100 tweets de cuentas locales

2. **Filtro Temporal**
   - Descarta noticias con más de 1 hora
   - Usa fecha de publicación o fecha en el texto

3. **Verificación de Duplicados**
   - Genera hash del contenido
   - Consulta PostgreSQL (últimas 24 horas)
   - Si existe → descarta

4. **Pre-filtrado**
   - Palabras clave de alto impacto
   - Descarta noticias irrelevantes rápidamente

5. **Análisis con IA**
   - OpenAI clasifica relevancia
   - Extrae severidad (1-10)
   - Identifica ubicación específica
   - Detecta víctimas e impacto

6. **Geolocalización**
   - Geocodifica ubicación extraída
   - Calcula distancia a cada Costco
   - Verifica radio de 3 km
   - Verifica vialidades clave

7. **Notificación y Guardado**
   - Envía alerta a Telegram
   - Guarda en PostgreSQL con todos los campos
   - Marca como procesada localmente

---

## 🎯 Próximos Pasos

### Dashboards y Visualizaciones
- [ ] Dashboard en tiempo real con Streamlit/Grafana
- [ ] Mapa de calor de eventos
- [ ] Gráficas de tendencias por tipo de evento
- [ ] Reportes semanales/mensuales automatizados

### Mejoras de IA
- [ ] Clasificación de impacto en operaciones de Costco
- [ ] Predicción de duración del evento
- [ ] Recomendaciones de acciones a tomar

### Integraciones
- [ ] Webhook para sistemas internos de Costco
- [ ] API REST para consultas externas
- [ ] Exportación a Excel/PDF de reportes

### Monitoreo Expandido
- [ ] Más fuentes de noticias locales
- [ ] Monitoreo de Facebook/Instagram
- [ ] Alertas de tráfico en tiempo real (Waze API)

---

## 📞 Soporte y Documentación

- **Guía de PostgreSQL:** `GUIA_CONFIGURACION_POSTGRESQL_RAILWAY.md`
- **Repositorio:** https://github.com/Eugeh13/costco-news-monitor
- **Railway:** https://railway.app/
- **OpenAI API:** https://platform.openai.com/docs/

---

## 📝 Notas Técnicas

### Limitaciones de Rate Limits
- **OpenAI:** 3 RPM (requests por minuto) en tier gratuito
- **Nominatim:** 1 request por segundo
- **Twitter:** Limitado por cookies de autenticación

### Manejo de Errores
- Fallback a método tradicional si falla IA
- Reintentos automáticos en geocodificación
- Logs detallados para debugging

### Zona Horaria
- Todas las fechas en CST (America/Chicago)
- Conversión automática de timestamps
- Formato: `DD/MM/YYYY HH:MM CST`

---

## ✅ Checklist de Verificación

- [x] Sistema desplegado en Railway
- [x] OpenAI API configurada y funcionando
- [x] Twitter scraping con twscrape operativo
- [x] Filtro temporal de 1 hora activo
- [x] Notificaciones a Telegram funcionando
- [x] PostgreSQL configurado
- [x] Tabla de noticias creada
- [x] Detección de duplicados activa
- [x] Guardado en DB funcionando
- [x] Ejecución programada cada 30 minutos
- [x] Zona horaria CST configurada
- [x] Logs detallados habilitados

---

## 🎉 Estado del Proyecto

**✅ SISTEMA COMPLETAMENTE OPERATIVO**

- Desplegado en Railway
- Análisis de IA funcionando
- Twitter integrado
- Base de datos PostgreSQL activa
- Detección de duplicados implementada
- Monitoreo cada 30 minutos
- Alertas a Telegram operativas

---

**Desarrollado para Costco Monterrey** 🛒  
**Versión:** 2.0 (con PostgreSQL y detección de duplicados)  
**Última actualización:** Noviembre 2025
