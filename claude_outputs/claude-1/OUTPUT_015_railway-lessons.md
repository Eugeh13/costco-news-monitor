# OUTPUT_015 — docs/RAILWAY_LESSONS.md: lecciones aprendidas Railway + PostgreSQL + Python

**Fecha:** 2026-04-23
**Worker:** claude-1
**Rama trabajada:** docs/railway-lessons
**Commit(s):** pendiente

## Qué se hizo

Creado `docs/RAILWAY_LESSONS.md` — documento de referencia para evitar repetir 6 horas de debugging de Railway. Basado en la sesión del 22-23 abril 2026 del proyecto costco-news-monitor v2.

## Secciones del documento

| Sección | Contenido |
|---------|-----------|
| **1. Setup correcto desde día 1** | Imagen, POSTGRES_USER/PASSWORD literales, volumen, Railpack vs Nixpacks, Procfile, requirements.txt |
| **2. Bugs conocidos** | Credenciales rotatorias con `${{secret()}}`, asyncpg vs TCP Proxy, `railway run` sin túnel, volúmenes no validados, Nixpacks deprecated |
| **3. Workarounds que sí funcionan** | Pre-deploy commands para migraciones, validar credenciales con `SELECT current_user`, `load_dotenv()` en módulos Python |
| **4. Checklist de setup nuevo proyecto** | 13 pasos ordenados desde crear proyecto vacío hasta verificar logs del worker |
| **5. Errores que NO repetir** | Tabla de 6 anti-patrones con alternativas |
| **6. Comandos de diagnóstico rápido** | `nc`, `railway run python3 -c`, asyncpg test snippet |

## Archivos creados/modificados

| Archivo | Cambio |
|---------|--------|
| `docs/RAILWAY_LESSONS.md` | Nuevo — 9 KB, 6 secciones |

## Tests

No aplica (documento de texto).

## Commit hash verificado

pendiente
