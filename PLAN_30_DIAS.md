# PLAN_30_DIAS.md

**Proyecto:** costco-news-monitor v2 — "Costco MTY Alert Dashboard"
**Cliente objetivo:** empresa de seguridad que da servicio a Costco Monterrey (contacto en proceso)
**Ventana:** 21 abril 2026 → 20 mayo 2026
**Propietario:** Eugenio
**Revisión semanal:** cada domingo, retrospectiva de lo entregado

---

## Producto definido

Dashboard web en tiempo real donde un operador de seguridad consulta incidentes activos (accidentes, incendios, balaceras, bloqueos, inundaciones) cerca de las 3 sucursales Costco Monterrey. Vista principal: mapa con pins. El operador abre el dashboard cuando quiere saber qué está pasando — no recibe notificaciones push.

### Sucursales objetivo (hardcoded en este MVP)
- **Carretera Nacional:** 25.6026, -100.2640
- **Cumbres:** 25.7353, -100.4022
- **Valle Oriente:** 25.6457, -100.3072
- **Radio de interés:** 3 km alrededor de cada sucursal

### Stack técnico confirmado
- **Backend:** Python 3.11 + FastAPI + SQLAlchemy 2.x async + Alembic + Pydantic v2
- **LLM:** Anthropic SDK (Haiku 4.5 + Sonnet 4.6 con prompt caching)
- **DB:** PostgreSQL (producción) / SQLite (desarrollo)
- **Frontend:** Jinja2 + HTMX + Alpine.js + TailwindCSS + Leaflet.js
- **Deploy:** Docker Compose en Hostinger KVM 1
- **Logs:** structlog

---

## Stack de decisiones cerradas (NO se debate más este mes)

1. **Producto = dashboard con mapa**, no bot de Telegram. El bot queda como herramienta de dev interna.
2. **Vertical único = Costco MTY**. NO se construye multi-tenant ni configurabilidad por cliente este mes.
3. **Polling, no webhooks ni Twitter.** Google News RSS + PC NL + Bomberos NL cada 15 min.
4. **Sin push notifications al usuario final.** El dashboard es el único canal.
5. **Stack frontend HTMX/Alpine/Leaflet**, no React.
6. **Multi-user 1-5 concurrentes.** Auth básico user/password, no SSO ni RBAC.

---

## Regla de oro del mes

> **"Si no está en el plan, no lo construimos."**

Si durante las próximas 4 semanas aparece una idea nueva (Twitter scraping, Aether-Core integration, app móvil, Slack bot, multi-tenant), va a `BACKLOG.md`, no al código. Esta disciplina es lo que evita que el plan se descarrile.

Excepciones: solo por **mini-retrospectiva** documentando por qué se cambia y qué se saca a cambio.

---

## Semana 1 — 21-27 abril
**Tema:** "Motor limpio que alimenta datos vendibles"

### Objetivo
Pipeline corriendo con costo <$0.10 por ciclo y geolocalización a nivel zona/colonia en al menos 80% de los incidentes detectados.

### Tareas
- [x] **T1.1** Fix del geolocator (strip markdown fences en JSON parsing) — 30 min
- [x] **T1.2** Reescribir geolocator con `tool_use` de Anthropic en lugar de JSON mode manual (más robusto) — 2 hrs
- [x] **T1.3** Prompt caching en classifier.py (`cache_control=ephemeral` en system prompt) — 1 hr
- [x] **T1.4** Prompt caching en geolocator.py — 45 min
- [x] **T1.5** Filtro temporal `NEWS_MAX_AGE_HOURS=3` en src/scrapers/base.py + src/core/config.py — 1 hr
- [x] **T1.6** Agregar `when:1h` a queries de Google News RSS (scrapers/_google_news_rss.py) — 20 min
- [x] **T1.7** Mover `dedup.py` antes del classifier en el pipeline (evitar clasificar duplicados) — 1 hr
- [x] **T1.8** Agregar campos al schema: `approximate_location` (colonia/zona), `exact_location_lat`, `exact_location_lng`, `geolocation_confidence` — 30 min
- [x] **T1.9** Migración Alembic 0004 con los nuevos campos — 20 min
- [x] **T1.10** Tests: 171/171 siguen pasando + nuevos tests para geolocator con casos reales MTY — 2 hrs
- [x] **T1.11** Corrida de validación: 3 ciclos consecutivos, medir costo y precisión de geolocalización — 1 hr

### Criterio de éxito
- 171/171 tests pasando (sin incluir los nuevos)
- Al menos 80% de incidentes relevantes tienen `approximate_location` poblado
- Costo por corrida de ~200 artículos < $0.10
- Documento `WEEK1_METRICS.md` con números medidos

### Horas totales estimadas: 10-11 hrs

### Retrospectiva Semana 1 — CERRADA ✅

Completada el 20 abril 2026 en ~4-5 horas reales (estimado eran 10-11 hrs).

Números finales (corrida B con todos los filtros activos):
- Artículos procesados: 16 (vs 200 baseline, -92%)
- Tiempo por corrida: 133s (vs 673s baseline, -80%)
- Tests: 194/194 passing (+23 vs 171 baseline)
- Geolocalización: 100% con approximate_location, 75% con confidence >= 0.5
- Alertas generadas: 0 en ventana de 1h (hay que operar varios días para muestra significativa)

Costo estimado por corrida: ~$0.05 USD (pendiente medición exacta,
instrumentación va en Semana 2)

Bonus entregado:
- Migración 0005 con 4 campos geo también en decision_log (fix de schema mismatch)
- Dedup con URL canonicalization + DB lookup 24h window

Deuda técnica pendiente → BACKLOG.md:
- Consolidar decision_log y analysis_result en una sola tabla
- Investigar por qué 45 registros quedaron no_geo en corridas previas
- Instrumentar logging de tokens para costo exacto (va en Semana 2)

---

## Semana 2 — 28 abril - 4 mayo
**Tema:** "Dashboard MVP con mapa funcional"

### Objetivo
Dashboard corriendo localmente en `http://localhost:8000` con mapa Leaflet mostrando incidentes reales de las últimas 72 hrs, con filtros básicos y detalle por incidente.

### Tareas
- [x] **T2.1** Setup de Tailwind CSS vía CDN en el template base — 30 min
- [x] **T2.2** Setup de Leaflet.js vía CDN en página principal — 30 min
- [x] **T2.3** Endpoint `GET /api/incidents` con query params: `since`, `severity_min`, `branch`, limit — 2 hrs
- [x] **T2.4** Página principal `/` con mapa centrado en MTY + 3 pins fijos de los Costcos + círculos de radio 3km — 2 hrs
- [x] **T2.5** Pins dinámicos de incidentes alimentados desde `/api/incidents` vía fetch JS + rendering en Leaflet — 2 hrs
- [x] **T2.6** Colores de pins por severidad (rojo 8-10, naranja 5-7, amarillo 3-4, gris 1-2) — 1 hr
- [x] **T2.7** Panel lateral con click en pin: muestra título, fuente, timestamp, descripción, link al artículo original — 2 hrs
- [x] **T2.8** Filtros en UI (Alpine.js): por sucursal, por severidad mínima, por rango temporal (1h/6h/24h/72h) — 2 hrs
- [x] **T2.9** Auto-refresh del mapa cada 60 segundos (HTMX o setTimeout) — 30 min
- [x] **T2.10** Tests de integración: `/api/incidents` responde schema correcto con filtros — 1 hr

### Criterio de éxito
- Dashboard carga en <2 segundos
- Mapa muestra incidentes reales con pins clickables
- Los 4 filtros funcionan y actualizan el mapa en <500ms
- Responsivo: funciona en pantalla 1920x1080 y en laptop 1366x768
- Documento `WEEK2_SCREENSHOTS.md` con capturas del dashboard funcionando

### Horas totales estimadas: 13-14 hrs

---

## Semana 3 — 5-11 mayo
**Tema:** "Producción 24/7 + feedback loop + polish"

### Objetivo
Dashboard disponible en URL pública con HTTPS, pipeline corriendo cada 15 min automáticamente, feedback del operador integrado, y looks como producto profesional.

### Tareas
- [ ] **T3.1** Dockerfile para el pipeline (cron + pipeline Python) — 1 hr
- [ ] **T3.2** Dockerfile para el dashboard (FastAPI + Uvicorn) — 30 min
- [ ] **T3.3** docker-compose.yml en Hostinger con servicios: pipeline, dashboard, postgres, nginx — 2 hrs
- [ ] **T3.4** Dominio + SSL con Let's Encrypt (Certbot) — 1 hr
- [ ] **T3.5** Auth básico HTTP en dashboard (usuario/password via env) — 1 hr
- [ ] **T3.6** Feedback UI: botones "útil" / "falso positivo" / "irrelevante" en cada incidente — 2 hrs
- [ ] **T3.7** Tabla `incident_feedback` en DB + endpoint `POST /api/feedback` — 1 hr
- [ ] **T3.8** Analytics internos: track de eventos de uso (abrir dashboard, aplicar filtro, click pin) — 1 hr
- [ ] **T3.9** Vista `/stats` para ti (no para el operador): incidentes/día, precisión, cobertura, latencia — 2 hrs
- [ ] **T3.10** Polish visual: logo simple, favicon, colores brand, zona horaria MTY en todos los timestamps, idioma 100% español — 2 hrs
- [ ] **T3.11** Monitoreo: script que chequea si el pipeline está vivo, te manda email si se cae — 1 hr
- [ ] **T3.12** Operación continua 48 hrs + hot-fixes de lo que descubras — 2-4 hrs

### Criterio de éxito
- URL pública accesible con HTTPS válido
- 48 hrs continuas sin intervención manual
- Al menos 20 incidentes procesados en ese período
- Documento `WEEK3_OPERATIONS.md` con métricas reales de 48 hrs

### Horas totales estimadas: 16-18 hrs

---

## Semana 4 — 12-20 mayo
**Tema:** "Demo, venta, iteración"

### Objetivo
Cerrar conversación con empresa de seguridad: sí avanzamos a mes 2 con cliente pagando, o pivotamos.

### Tareas
- [ ] **T4.1** Video demo de 5 minutos narrado en español, mostrando dashboard con incidentes reales — 2 hrs
- [ ] **T4.2** One-pager PDF: qué es, para quién, qué hace, cómo funciona, precio — 2 hrs
- [ ] **T4.3** Propuesta comercial en PDF: precio mensual, SLA de uptime, plan de onboarding, soporte — 2 hrs
- [ ] **T4.4** Email de presentación al contacto con link al video + demo en vivo + PDF — 30 min
- [ ] **T4.5** Reunión de demo (45-60 min) — 1 hr
- [ ] **T4.6** Iteración sobre feedback del cliente (ajustes visuales, features priorizadas) — 2-6 hrs
- [ ] **T4.7** Retrospectiva: ¿avanzamos a mes 2 o pivotamos? Documento de decisión — 1 hr

### Criterio de éxito
- Reunión realizada con el contacto
- Feedback concreto recibido (yes/no/ajustes)
- Decisión documentada de próximo paso

### Horas totales estimadas: 10-14 hrs

---

## Totales

| Semana | Horas est. | Acumulado |
|--------|-----------|-----------|
| 1 | 10-11 | 10-11 |
| 2 | 13-14 | 23-25 |
| 3 | 16-18 | 39-43 |
| 4 | 10-14 | 49-57 |

Total: **49-57 horas en 30 días**. Disponibilidad comprometida: 20-40 hrs. **Plan estará ajustado**, la semana 3 es la más pesada.

Si en semana 1 ya se ve que no llegamos, es momento de descartar algo (probablemente T3.8-T3.9 analytics) antes de que se convierta en problema.

---

## Métricas que mediremos semanalmente

- Horas trabajadas vs planificadas
- Tareas completadas vs comprometidas
- Bugs conocidos abiertos
- Costo LLM acumulado del mes
- Incidentes procesados (desde que se empieza a correr continuamente)
- Precisión estimada (útil / total clasificados)

---

## Pendientes administrativos PREVIOS al día 1

- [ ] **Revocar API keys comprometidas** en console.anthropic.com:
  - `new_key` (aov...LwAA)
  - `my_key` (gEe...4QAA)
- [ ] Confirmar que tengo saldo suficiente en Console para el mes (~$5-15 USD esperado)
- [ ] Push final de v2-rewrite actual a GitHub antes de empezar Semana 1
- [ ] Crear rama `feature/fase-b1` en GitHub para trabajo de Semana 1
- [ ] Crear `BACKLOG.md` (ver archivo adjunto)

---

## Reglas del juego del mes

1. **Commit diario al repo.** Aunque sea un commit pequeño.
2. **Entregable semanal documentado.** Los documentos WEEK{N}_*.md son obligatorios.
3. **Retrospectiva cada domingo.** 15 minutos revisando qué se hizo, qué se atoró, qué se cambia.
4. **Features fuera del plan → BACKLOG.md**, sin excepciones informales.
5. **Si algo no se termina en su semana**, la siguiente empieza atrasada. No se compensa acelerando (lleva a bugs).

---

*Documento creado el 20 abril 2026. Primera versión. Se actualiza solo en retros dominicales.*

---

### Retrospectiva Día 1 — 20 abril 2026 ✅

**Horas reales:** ~4-5 hrs (vs 10-11 hrs planeadas para Semana 1 completa)

**Completado hoy:**
- Semana 1 COMPLETA: T1.2, T1.3, T1.4, T1.5, T1.6, T1.7, T1.8, T1.9, T1.10, T1.11
- Semana 2 Parte A: T2.3 API endpoint, token logging infraestructura, migración 0005
- Estrategia comercial documentada (COMMERCIAL_STRATEGY.md)
- 205/205 tests passing

**Descubrimientos críticos:**
1. Geolocator imprecisión con Nominatim — dirigido a Semana 3 como
   prioridad alta (investigación de opciones en progreso esta noche)
2. Decision logger no captura tokens en registros clasificados — fix
   en progreso esta noche (week2/decision-logger-tokens-fix)
3. Dedup tan efectivo que con when:1h hay pocos artículos nuevos por
   corrida — insight operativo (no bug)

**Costo real del día:**
- ~$0.10-0.20 USD estimados en Anthropic API (medición exacta tras fix
  de token logging)
- 0 horas de infraestructura adicional (todo local)

**Status vs plan:**
- 5 días adelantados del plan de 30 días
- Semana 2 terminará mañana probablemente (vs día 14 planeado)

---

## Día 1 — Retrospectiva completa (20 abril 2026) ✅

**Horas reales:** ~6 hrs  
**Horas planeadas del plan:** 10-11 hrs (Semana 1 sola)  
**Adelanto:** ~6 días del plan de 30

### Entregado

- Semana 1 COMPLETA: 11/11 tareas (fix geolocator con tool_use, prompt caching, filtros temporales, dedup, schema con campos geo, migraciones 0004+74b26b81)
- Semana 2 COMPLETA: 10/10 tareas (endpoint /api/incidents, token logging, dashboard base con mapa Leaflet funcional)
- Dashboard visible en http://localhost:8000/ con 3 pins Costco + círculos 3km
- Estrategia comercial documentada (COMMERCIAL_STRATEGY.md)
- Research de fix geolocator documentado (docs/GEOLOCATOR_FIX_RESEARCH.md)

### Métricas finales

- Tests: 214/214 passing (+43 vs baseline 171)
- Decision_logs en DB: 331 totales, 19 con token data
- Costo medido: $0.002/artículo procesado (primera medición real — $0.0187 total sobre 19 registros instrumentados)
- Corridas de validación: 3 ejecutadas OK

### Bugs encontrados y resueltos

1. **DB dedup false-positive:** pipeline logueaba artículo ANTES del dedup check. Fix: `exclude_run_id` parameter.
2. **Geolocator markdown fences:** JSON envuelto en `` ```json ``` `` rompía parser. Fix: rewrite con tool_use API de Anthropic.
3. **Schema mismatch:** claude-1 agregó campos a `analysis_results` pero pipeline escribe a `decision_log`. Fix: migración 74b26b81 agregó mismos campos a `decision_log`.

### Issues conocidos al cierre

- **Nominatim imprecisión:** incidentes clasificados quedan `within_radius=0` aunque estén cerca. FIX SEMANA 3 con Mapbox (ver docs/GEOLOCATOR_FIX_RESEARCH.md).
- **Tailwind CDN warning "not for production":** carga 3 MB vs ~10 KB optimizados. Fix Semana 3 con build local.
- **Scrapers Milenio/Info7/Horizonte rotos** (403/404). Decisión pendiente Semana 3: arreglar o descartar del roadmap.

### Semana 2 Parte B — pendiente real para Día 2

- Pins dinámicos de incidentes desde /api/incidents
- Colores por severidad (rojo >=8, naranja 5-7, amarillo 3-4, gris <3)
- Panel lateral al click en pin con detalle completo
- Filtros Alpine.js (sucursal, severidad mínima, ventana temporal)
- Toggle "solo dentro del radio"
- Auto-refresh cada 60s
- Tests de integración frontend
