# Sistema de Monitoreo de Noticias de Alto Impacto - Monterrey

Sistema automatizado para monitorear noticias de alto impacto que ocurran en un radio de 5 kilómetros alrededor de las 3 sucursales de Costco en Monterrey, Nuevo León, México.

## Características

- **Monitoreo en tiempo real** de portales de noticias locales
- **Detección automática** de noticias de alto impacto en 5 categorías:
  - Accidentes viales graves
  - Incendios
  - Situaciones de riesgo y seguridad
  - Bloqueos de vialidades
  - Desastres naturales
- **Geolocalización** de eventos y cálculo de distancia a sucursales Costco
- **Filtrado inteligente** basado en palabras clave y ubicación
- **Notificaciones** en consola (extensible a email y Telegram)
- **Prevención de duplicados** mediante registro de noticias procesadas

## Sucursales Monitoreadas

1. **Costco Carretera Nacional**
   - Dirección: Carretera Nacional Km. 268 +500 5001, Monterrey, NL 64989
   - Coordenadas: 25.5781498, -100.2512201

2. **Costco Cumbres**
   - Dirección: Alejandro de Rodas 6767, Monterrey, NL 64344
   - Coordenadas: 25.7295984, -100.3927985

3. **Costco Valle Oriente**
   - Dirección: Av. Lázaro Cárdenas 800, San Pedro Garza García, NL 66269
   - Coordenadas: 25.6396949, -100.317631

## Fuentes de Información

### Portales de Noticias
- Milenio Monterrey
- INFO 7
- El Horizonte

### Cuentas de Twitter/X (requiere API)
- @pc_mty (Protección Civil Monterrey)
- @mtytrafico (Tráfico MTY)
- @seguridadmtymx (Seguridad Monterrey)

## Instalación

### Requisitos Previos
- Python 3.11 o superior
- pip (gestor de paquetes de Python)

### Pasos de Instalación

1. **Clonar o descargar el proyecto**
   ```bash
   cd news_monitor_app
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

   O instalar manualmente:
   ```bash
   pip install requests beautifulsoup4 geopy
   ```

## Uso

### Ejecución Única

Para ejecutar el monitoreo una sola vez:

```bash
python main.py
```

### Ejecución Continua

Para ejecutar el monitoreo de forma continua (cada 15 minutos), editar el archivo `main.py` y descomentar la línea:

```python
# monitor.run_continuous(interval_minutes=15)
```

Luego ejecutar:

```bash
python main.py
```

### Ejecución Programada con Cron

Para ejecutar el script automáticamente cada 15 minutos usando cron:

1. Abrir el editor de crontab:
   ```bash
   crontab -e
   ```

2. Agregar la siguiente línea:
   ```
   */15 * * * * cd /ruta/a/news_monitor_app && /usr/bin/python3 main.py >> monitor.log 2>&1
   ```

## Estructura del Proyecto

```
news_monitor_app/
├── main.py                 # Script principal
├── config.py               # Configuración (coordenadas, palabras clave, fuentes)
├── scraper.py              # Módulo de scraping de noticias
├── analyzer.py             # Módulo de análisis y filtrado
├── geolocation.py          # Módulo de geolocalización y cálculo de distancias
├── notifier.py             # Módulo de notificaciones
├── storage.py              # Módulo de gestión de duplicados
├── requirements.txt        # Dependencias del proyecto
├── README.md               # Este archivo
└── processed_news.txt      # Archivo de registro (se crea automáticamente)
```

## Configuración

### Modificar Radio de Búsqueda

Editar el archivo `config.py` y cambiar el valor de `RADIUS_KM`:

```python
RADIUS_KM = 5.0  # Cambiar a la distancia deseada en kilómetros
```

### Agregar Palabras Clave

Editar el diccionario `KEYWORDS` en `config.py`:

```python
KEYWORDS = {
    "accidente_vial": [
        "choque", "accidente", "volcadura", "atropello", ...
    ],
    ...
}
```

### Agregar Fuentes de Noticias

Editar la lista `NEWS_SOURCES` en `config.py`:

```python
NEWS_SOURCES = [
    {
        "nombre": "Nombre del Portal",
        "url": "https://ejemplo.com",
        "tipo": "portal"
    },
    ...
]
```

## Ejemplo de Notificación

```
======================================================================
🚨 ALERTA DE NOTICIA DE ALTO IMPACTO 🚨
======================================================================

📅 Fecha y Hora: 2025-10-25 14:30:00
📍 Tipo de Evento: Accidente Vial
📰 Titular: Fuerte choque en Av. Gonzalitos deja varios heridos

🗺️  Ubicación Detectada: Av. Gonzalitos con Av. Madero
📏 Proximidad: A 3.2 km de Costco Cumbres
🏢 Dirección Costco: Alejandro de Rodas 6767, Monterrey, NL 64344

📡 Fuente: Milenio Monterrey
🔗 URL: https://www.milenio.com/monterrey/accidente-gonzalitos

📝 Resumen:
Un fuerte accidente vehicular se registró la tarde de este viernes
en el cruce de Av. Gonzalitos con Av. Madero...

======================================================================
```

## Extensiones Futuras

### Notificaciones por Email

Para habilitar notificaciones por email, configurar SMTP en `notifier.py` y actualizar `config.py`:

```python
NOTIFICATION_CONFIG = {
    "console": True,
    "email": True,
}

EMAIL_CONFIG = {
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "sender_email": "tu_email@gmail.com",
    "sender_password": "tu_contraseña",
    "recipient_email": "destinatario@example.com"
}
```

### Notificaciones por Telegram

1. Crear un bot de Telegram con @BotFather
2. Obtener el token del bot
3. Obtener tu chat ID
4. Configurar en `config.py`:

```python
NOTIFICATION_CONFIG = {
    "console": True,
    "telegram": True,
}

TELEGRAM_CONFIG = {
    "bot_token": "TU_BOT_TOKEN",
    "chat_id": "TU_CHAT_ID"
}
```

### Integración con Twitter API

Para monitorear cuentas de Twitter en tiempo real:

1. Crear una cuenta de desarrollador en Twitter
2. Obtener API keys
3. Instalar `tweepy`: `pip install tweepy`
4. Implementar streaming en `scraper.py`

## Limitaciones

- **Scraping de Twitter**: El acceso a Twitter/X sin API es limitado. Se recomienda usar la API oficial (requiere suscripción de pago).
- **Geocodificación**: Depende de la calidad de la información de ubicación en las noticias.
- **Estructura de sitios web**: Los scrapers pueden necesitar ajustes si los sitios web cambian su estructura HTML.

## Solución de Problemas

### Error de geocodificación

Si el sistema no puede geocodificar ubicaciones:
- Verificar conexión a internet
- El servicio Nominatim tiene límites de tasa (1 petición por segundo)
- Considerar usar un servicio de geocodificación alternativo (Google Maps API, Mapbox)

### No se encuentran noticias

- Verificar que las URLs de las fuentes sean correctas
- Los sitios web pueden haber cambiado su estructura HTML
- Revisar los selectores CSS en `scraper.py`

### Duplicados

Si se reciben notificaciones duplicadas:
- Verificar que el archivo `processed_news.txt` tenga permisos de escritura
- El sistema mantiene un registro de URLs procesadas

## Contribuciones

Este es un proyecto de código abierto. Las mejoras sugeridas incluyen:
- Soporte para más fuentes de noticias
- Mejoras en la extracción de ubicaciones
- Interfaz web para visualización
- Base de datos para almacenamiento histórico
- Machine Learning para clasificación de noticias

## Licencia

Este proyecto se proporciona "tal cual" para fines educativos y de demostración.

## Autor

Desarrollado por Manus AI

## Contacto

Para preguntas o sugerencias sobre este proyecto, consultar la documentación o contactar al desarrollador.

