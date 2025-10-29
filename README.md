# 🚨 Sistema de Monitoreo de Noticias - Costco Monterrey

Sistema automatizado de monitoreo de noticias de alto impacto (accidentes, incendios, balaceras, bloqueos) cerca de sucursales Costco en Monterrey, NL.

**Versión**: 2.1 con Inteligencia Artificial  
**Powered by**: OpenAI GPT-4o-mini

---

## 🎯 Características

- ✅ **Análisis con IA**: Comprensión semántica de noticias usando OpenAI
- ✅ **Clasificación de Severidad**: Escala 1-10 (MENOR/MODERADA/GRAVE/CRÍTICA)
- ✅ **Filtro Temporal**: Solo noticias de última hora (máximo 1 hora de antigüedad)
- ✅ **Geocodificación**: Ubicación precisa de eventos
- ✅ **Radio de Monitoreo**: 3 km alrededor de cada Costco
- ✅ **Notificaciones Telegram**: Alertas en tiempo real
- ✅ **Ejecución Automática**: Cada 30 minutos, 24/7

---

## 📍 Ubicaciones Monitoreadas

### 1. Costco Carretera Nacional
- **Dirección**: Carretera Nacional Km. 268, Monterrey, NL
- **Radio**: 3 km

### 2. Costco Cumbres
- **Dirección**: Alejandro de Rodas 6767, Monterrey, NL
- **Radio**: 3 km

### 3. Costco Valle Oriente
- **Dirección**: Av. Lázaro Cárdenas 800, San Pedro Garza García, NL
- **Radio**: 3 km

---

## 🎯 Eventos Monitoreados

- 🚗 **Accidentes Viales**: Choques, volcaduras, atropellos
- 🔥 **Incendios**: Edificios, locales, vehículos
- 🚨 **Seguridad**: Balaceras, enfrentamientos
- 🚧 **Bloqueos**: Manifestaciones, cierres viales
- 🌊 **Desastres Naturales**: Inundaciones, trombas

---

## 🚀 Despliegue en Railway

### Paso 1: Conectar GitHub

1. Ve a [Railway.app](https://railway.app/)
2. Haz clic en "Start a New Project"
3. Selecciona "Deploy from GitHub repo"
4. Conecta tu cuenta de GitHub
5. Selecciona este repositorio

### Paso 2: Configurar Variables de Entorno

En Railway, ve a "Variables" y agrega:

```
TELEGRAM_BOT_TOKEN=tu_token_aqui
TELEGRAM_CHAT_ID=tu_chat_id_aqui
OPENAI_API_KEY=tu_openai_api_key_aqui
```

### Paso 3: Desplegar

Railway detectará automáticamente el `requirements.txt` y desplegará el proyecto.

El sistema iniciará automáticamente con `run_scheduled_ai.py`.

---

## 📦 Instalación Local

### Requisitos

- Python 3.11+
- pip3

### Pasos

1. **Clonar repositorio**:
```bash
git clone https://github.com/tu-usuario/news-monitor-costco.git
cd news-monitor-costco
```

2. **Instalar dependencias**:
```bash
pip3 install -r requirements.txt
```

3. **Configurar variables de entorno**:
```bash
export TELEGRAM_BOT_TOKEN="tu_token"
export TELEGRAM_CHAT_ID="tu_chat_id"
export OPENAI_API_KEY="tu_openai_key"
```

4. **Ejecutar**:

**Una vez** (prueba):
```bash
python3.11 main_ai.py
```

**Automático** (cada 30 minutos):
```bash
python3.11 run_scheduled_ai.py
```

---

## 📊 Costos Estimados

### OpenAI API
- **Por día**: $0.15 - $0.45 USD
- **Por mes**: $5 - $15 USD

### Railway Hosting
- **Gratis**: Hasta 500 horas/mes
- **Hobby Plan**: $5 USD/mes (ilimitado)

**Total estimado**: $10-20 USD/mes

---

## 📱 Ejemplo de Notificación

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

📡 Milenio Monterrey
🔗 [Ver noticia completa]

⏰ 28/10/2025 18:00
```

---

## 🔧 Configuración

### Cambiar Intervalo de Monitoreo

Edita `run_scheduled_ai.py`:
```python
# Cambiar intervalo (default: 30 minutos)
# Modificar función get_next_scheduled_time()
```

### Cambiar Ventana de Tiempo

Edita `main_ai.py`, línea 35:
```python
# Ventana de 1 hora (default)
self.time_filter = TimeFilter(max_age_hours=1)

# Ventana de 30 minutos
self.time_filter = TimeFilter(max_age_hours=0.5)
```

### Desactivar IA

Edita `main_ai.py`, línea 30:
```python
monitor = NewsMonitorAI(use_ai=False)
```

---

## 📚 Documentación

- **GUIA_MEJORAS_IA.md**: Documentación completa de mejoras con IA
- **FILTRO_TIEMPO_IMPLEMENTADO.md**: Explicación del filtro temporal
- **EXPLICACION_CRITERIOS_BUSQUEDA.md**: Criterios de búsqueda detallados
- **INICIO_RAPIDO_IA.md**: Guía de inicio rápido
- **ACTIVACION_AUTOMATICA.md**: Guía de activación automática

---

## 🛠️ Estructura del Proyecto

```
news_monitor_app/
├── main_ai.py              # Script principal con IA
├── run_scheduled_ai.py     # Ejecución programada
├── ai_analyzer.py          # Módulo de análisis con IA
├── time_filter.py          # Filtro temporal de noticias
├── scraper.py              # Scraping de noticias
├── analyzer.py             # Análisis tradicional
├── geolocation.py          # Geocodificación
├── notifier_ai.py          # Notificaciones mejoradas
├── storage.py              # Almacenamiento de noticias procesadas
├── config.py               # Configuración
├── requirements.txt        # Dependencias
└── README.md               # Este archivo
```

---

## 🧪 Pruebas

### Probar Módulo de IA
```bash
python3.11 ai_analyzer.py
```

### Probar Filtro de Tiempo
```bash
python3.11 time_filter.py
```

### Probar Notificador
```bash
python3.11 notifier_ai.py test
```

### Probar Sistema Completo
```bash
python3.11 main_ai.py
```

---

## 📊 Estadísticas

### Por Día
- **Monitoreos**: 48
- **Noticias analizadas**: ~1,440
- **Análisis con IA**: ~100-150
- **Alertas enviadas**: 0-5 (depende de eventos)

### Por Mes
- **Monitoreos**: ~1,440
- **Noticias analizadas**: ~43,200
- **Análisis con IA**: ~3,000-4,500

---

## 🔒 Seguridad

- ✅ Credenciales en variables de entorno
- ✅ No hay API keys en el código
- ✅ `.gitignore` configurado
- ✅ Logs locales sin datos sensibles

---

## 🤝 Contribuir

Este es un proyecto privado para Costco Monterrey.

---

## 📞 Soporte

Para preguntas o soporte, contacta al administrador del sistema.

---

## 📄 Licencia

Uso privado - Costco Monterrey

---

**Desarrollado con ❤️ para Costco Monterrey**  
**Powered by OpenAI GPT-4o-mini**
