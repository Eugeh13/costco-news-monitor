# BACKLOG.md

**Propósito:** estacionar todas las ideas buenas que NO hacemos en este mes (21 abril - 20 mayo 2026).

**Regla:** cuando tengas "se me ocurre X", va aquí. No al código.

**Revisión:** al final del mes, decidir qué del backlog entra al plan del mes 2.

---

## Features de producto

### Fuentes adicionales (prioridad MEDIA para mes 2)
- [ ] Twitter/X via API oficial ($100/mes Basic) o via RSSHub+Feedbin ($5-15/mes)
- [ ] Scraper propio de X con cuenta quemable (más arriesgado)
- [ ] Scraping directo de Milenio/Info7/Horizonte (arreglar los 403/404 actuales)
- [ ] Facebook pages de medios locales
- [ ] Reddit r/Monterrey streaming
- [ ] Reportes manuales vía formulario web (operador de Costco reporta lo que el bot no detectó)

### Notificaciones (prioridad BAJA)
- [ ] Telegram bot para alertas críticas (severidad >=8) — opcional
- [ ] Email digest diario/semanal para managers
- [ ] SMS para emergencias (Twilio)
- [ ] Slack/Teams integration si el cliente lo pide
- [ ] WhatsApp Business API (muy cara, solo si hay budget del cliente)

### Dashboard avanzado (prioridad MEDIA)
- [ ] Multi-user con roles (admin, operador, viewer)
- [ ] SSO con Google/Microsoft
- [ ] Modo oscuro
- [ ] Export de reportes (PDF/Excel)
- [ ] Heatmap de incidentes (tendencias geográficas)
- [ ] Timeline view complementaria al mapa
- [ ] Búsqueda full-text en incidentes pasados
- [ ] Vista de sucursal individual ("solo Cumbres")
- [ ] Alertas visuales cuando entra nuevo incidente (toast, sonido opcional)
- [ ] Historial de feedback del operador + métricas de precisión
- [ ] Modo móvil optimizado (responsive profundo)

### Motor / Pipeline (prioridad ALTA para mes 2)
- [ ] Aether-Core como backend del análisis (dogfooding de producto propio)
- [ ] Feedback loop que mejore el classifier (reentrenamiento con señales del operador)
- [ ] Circuit breaker por fuente (si PC NL se cae, no intentar más por X minutos)
- [ ] Batch API de Anthropic para análisis no-tiempo-real (50% descuento)
- [ ] Embeddings para dedup semántico (no solo por hash de título)
- [ ] Clasificador de "impacto en Costco específicamente" (además de severidad general)
- [ ] Extracción de entidades nombradas (calles, colonias, referencias geográficas)

### Geolocalización (prioridad ALTA para mes 2)
- [ ] Geocoding con Mapbox o Google Maps API para mejor precisión
- [ ] Resolver alias/toponimia local ("Macroplaza", "Pulgas", "Santa Lucía")
- [ ] Fuzzy matching contra colonias de Monterrey (catálogo de INEGI)
- [ ] Histórico de incidentes por zona (descubrir patrones)

---

## Generalización / Multi-tenant (prioridad BAJA — solo si Costco MTY vende)

- [ ] Configurabilidad de sucursales por cliente (tabla `locations`)
- [ ] Tipos de incidente personalizables
- [ ] Ventanas temporales de impacto configurables
- [ ] Onboarding automatizado para nuevo cliente
- [ ] Billing/suscripciones
- [ ] Dashboard admin para gestionar clientes
- [ ] White-label: logos y branding por cliente
- [ ] API REST documentada para integración

---

## Infraestructura y operación

- [ ] Observabilidad seria: Prometheus + Grafana
- [ ] Alertmanager para alertas operativas
- [ ] Backups automáticos diarios de PostgreSQL
- [ ] Disaster recovery plan documentado
- [ ] Health check endpoint `/health` con dependencies check
- [ ] CI/CD con GitHub Actions (auto-deploy en main)
- [ ] Staging environment separado de producción
- [ ] Load testing
- [ ] Rate limiting en la API pública (si se expone)
- [ ] CDN para assets estáticos
- [ ] Logs centralizados (Loki/Datadog)
- [ ] Decidir en Semana 3 si necesitamos frontend build toolchain real (Vite/esbuild) o seguimos con CDN de Tailwind/Alpine/Leaflet

---

## Marketing / comercial

- [ ] Landing page del producto (si vamos a SaaS)
- [ ] Documentación pública (Docusaurus?)
- [ ] Video demos por caso de uso
- [ ] Testimonios del primer cliente
- [ ] Blog técnico (cómo se construyó)
- [ ] Perfil en LinkedIn del producto
- [ ] Pitch deck para inversión (si el producto vende bien)

---

## Exploraciones técnicas

- [ ] ¿Tiene sentido usar un LLM local (Llama 3 via Ollama) para el triage y solo usar Anthropic para el deep analyze?
- [ ] ¿Cómo se vería este producto con agents (tool use iterativo en lugar de pipeline fijo)?
- [ ] ¿Vale la pena un modelo fine-tuned para clasificación de noticias MX?
- [ ] ¿Puedo empaquetar esto como skill de Claude para otros devs?

---

## Deuda técnica reconocida

- [ ] Remover el scraper de Twitter con cookies del v1 (no funciona, estorba)
- [ ] Decidir qué hacer con Milenio/Info7/Horizonte scrapers rotos (refactor o descartar)
- [ ] Tests de carga del dashboard
- [ ] Revisión de seguridad: ¿el endpoint `/api/incidents` debería requerir auth?
- [ ] Configuración de logging estructurado consistente en todos los módulos
- [ ] Documentación interna de cómo correr el proyecto localmente desde cero
- [ ] [DEUDA TÉCNICA Semana 1] Consolidar decision_log y analysis_result en una sola tabla de resultados (hoy divergidas por legacy)
- [ ] Investigar 45 registros históricos en no_geo (corridas de Op C)
- [ ] [SEMANA 3 URGENTE] Fix precisión geolocator. Nominatim resuelve calles/carreteras a centroides genéricos. Resultado: incidentes clasificados terminan con within_radius=0 aunque estén dentro de 3km. Opciones bajo investigación (ver docs/GEOLOCATOR_FIX_RESEARCH.md).
- [ ] [DEUDA OPERACIONAL] Scrapers rotos Milenio/Info7/Horizonte. Decidir Semana 3 si se arreglan o se descartan oficialmente del roadmap. Google News RSS cubre suficiente por ahora.
- [ ] [SEMANA 3] Migrar Tailwind CSS de CDN a build local (npm + Tailwind CLI). El CDN carga ~3 MB y muestra warning de producción; build optimizado ~10 KB.
- [ ] [INSIGHT] El endpoint /api/incidents devuelve 0 cuando within_radius_only=true porque los 28 incidentes clasificados tienen within_radius=0 y los 4 alerts históricos tienen within_radius=NULL. Se resolverá cuando el geolocator esté fixeado (Semana 3).

---

## Ideas locas que quizás son buenas

- [ ] Bot que reporta sentimiento general de MTY ("día tranquilo" vs "día agitado") basado en volumen de incidentes
- [ ] Integración con Waze API para cruzar datos de tráfico con incidentes de prensa
- [ ] Predicción: ¿qué día de la semana hay más incidentes cerca de cada Costco?
- [ ] Alertas preventivas: "históricamente a esta hora hay más accidentes en esta zona"
- [ ] Chatbot en el mismo dashboard para que el operador haga preguntas ("¿qué pasó ayer en Cumbres?")

---

## Cómo usar este archivo

1. **Durante el mes**: cada vez que tengas una idea nueva, agrégala aquí con descripción breve
2. **En retrospectiva dominical**: revisa si alguna de las nuevas ideas cambia la priorización
3. **Al final del mes**: este archivo es el insumo para planear el próximo mes
4. **Prioridades**: marca con ALTA / MEDIA / BAJA según lo que vayas aprendiendo

---

*Primera versión: 20 abril 2026. Se actualiza al vuelo.*
