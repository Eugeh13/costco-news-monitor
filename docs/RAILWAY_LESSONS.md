# Railway + PostgreSQL + Python — Lecciones aprendidas

**Proyecto:** costco-news-monitor v2  
**Sesión de origen:** 22-23 abril 2026  
**Tiempo invertido en aprender estas lecciones:** ~6 horas  
**Propósito:** Evitar repetir estos errores en futuros proyectos o sesiones.

---

## 1. Setup correcto Railway PostgreSQL + Python worker desde día 1

### Servicio PostgreSQL

| Parámetro | Valor correcto | Error común |
|-----------|---------------|-------------|
| Imagen | `postgres:18-alpine` | No usar templates de Railway — traen variables mal configuradas |
| `POSTGRES_USER` | `"postgres"` **literal** | Nunca usar `${{secret(N,...)}}` — genera usuarios efímeros rotatorios |
| `POSTGRES_PASSWORD` | Password alfanumérico de 32 chars **literal** | Nunca usar `${{secret()}}` — causa credenciales rotatorias en TCP Proxy |
| Volume | Mínimo 1 GB en `/var/lib/postgresql/data` | Sin volumen los datos se pierden en cada redeploy |
| TCP Proxy | **Enabled** desde el principio | Si se habilita después, puede requerir redeploy del worker también |

### Worker Python

| Archivo | Contenido correcto |
|---------|-------------------|
| `Procfile` | `worker: python3.11 scheduler.py` (NO `web:`) |
| `runtime.txt` | `python-3.11.x` |
| `requirements.txt` | Lista explícita de todas las dependencias de producción |
| Builder | **Railpack** (actual). Nixpacks está deprecated — Railway lo ignora |

### Variable `DATABASE_URL` en el worker

```
DATABASE_URL = ${{Postgres.DATABASE_URL}}
```

Esto hace que Railway inyecte la URL interna correcta (`postgres.railway.internal:5432`) automáticamente. NO hardcodear la URL pública.

---

## 2. Bugs conocidos de Railway con Python/PostgreSQL

### Bug crítico: TCP Proxy con credenciales rotatorias

**Síntoma:** Cada llamada a `railway run`, `railway connect` o cualquier conexión externa genera un username diferente de 32 chars aleatorios, y la autenticación falla:

```
FATAL: password authentication failed for user "idyuopbnugrkbycyhgublgfjysswaoji"
FATAL: password authentication failed for user "jpiqaunofhxbungxgpetgpvhjjgcvjwp"
```

**Causa:** Cuando `POSTGRES_USER` o `POSTGRES_PASSWORD` usan `${{secret(...)}}` en lugar de valores literales, Railway genera credenciales efímeras para el TCP Proxy que expiran antes de completar el handshake PostgreSQL.

**Fix:** Recrear el servicio Postgres con `POSTGRES_USER=postgres` y `POSTGRES_PASSWORD=<valor literal>`.

---

### Bug: asyncpg + TCP Proxy de Railway

**Síntoma:** `ConnectionResetError [Errno 54]` o `ConnectionDoesNotExistError` al conectar con asyncpg, incluso cuando la URL es válida.

**Por qué ocurre:** El TCP Proxy de Railway (pgbouncer) en modo `transaction` no es compatible con algunas operaciones de asyncpg (prepared statements, LISTEN/NOTIFY).

**Lo que NO funciona:**
- `?ssl=disable` en la URL
- `?sslmode=disable`  
- Cambiar `ssl=` en asyncpg.connect()
- `railway run` con variables inyectadas

**Lo que sí funciona:** Usar la URL interna (`postgres.railway.internal:5432`) desde dentro de Railway — o configurar pgbouncer en modo `session` en lugar de `transaction`.

---

### Bug: `railway run` no crea túnel de red

**Síntoma:** `railway run python3 script.py` inyecta las variables de entorno de Railway, pero `postgres.railway.internal` no resuelve localmente:

```python
socket.getaddrinfo('postgres.railway.internal', 5432)
# → [Errno 8] nodename nor servname provided
```

**Conclusión:** `railway run` es solo inyección de variables. NO es un entorno Railway — los procesos corren en tu Mac sin acceso a la red interna de Railway.

---

### Bug: volúmenes no validados en deploy

**Síntoma:** El deploy aparece como exitoso pero el volumen queda en estado `staged` sin datos persistidos. Si el worker falla 3 veces seguidas, Railway puede recrear el volumen.

**Fix:** Si el deploy falla repetidamente, crear un volumen nuevo en el servicio Postgres en lugar de reintentar con el mismo.

---

### Bug: Nixpacks ignorado por Railway

**Síntoma:** `nixpacks.toml` presente en el repo pero Railway no instala dependencias — falla con `ModuleNotFoundError: No module named 'structlog'`.

**Causa:** Railway migró de Nixpacks a Railpack. El archivo `nixpacks.toml` es ignorado completamente.

**Fix:** Crear `requirements.txt` con todas las dependencias de producción + eliminar `nixpacks.toml`.

---

## 3. Workarounds que sí funcionan

### Migraciones desde local cuando TCP Proxy falla

**No se puede** correr `alembic upgrade head` desde Mac si el TCP Proxy está roto.

**Workaround:** Usar el **pre-deploy command** de Railway:

1. En Railway → servicio worker → **Settings**
2. Buscar **"Pre-deploy Command"** o **"Start Command"**
3. Agregar antes del comando principal:

```
python3 scripts/fix_alembic_version_col.py && python3 -m alembic upgrade head
```

Esto corre las migraciones dentro de Railway donde `postgres.railway.internal` sí es accesible.

---

### Validar credenciales del TCP Proxy

```bash
psql -h centerbeam.proxy.rlwy.net -p 55487 -U postgres -d railway
```

Dentro de psql, ejecutar:

```sql
SELECT current_user, current_database();
```

- Si devuelve `postgres | railway` → credenciales correctas, TCP Proxy sano.
- Si devuelve un string de 32 chars aleatorios → bug de credenciales rotatorias, recrear el servicio Postgres.

---

### Cargar .env en Python sin export dances

En lugar del anti-patrón `export $(grep -v '^#' .env | xargs)`, agregar al módulo Python que arranca primero:

```python
from dotenv import load_dotenv
load_dotenv()
```

Aplicar en: `src/dashboard/database.py`, `alembic/env.py`, scripts de utilidad.

---

## 4. Checklist de setup correcto al crear nuevo proyecto Railway

```
[ ] 1. Crear proyecto vacío en Railway
[ ] 2. Add service → Database → PostgreSQL (NO template predefinido)
[ ] 3. ANTES del primer deploy, verificar en Variables del servicio Postgres:
        POSTGRES_USER  = postgres          ← literal, no ${{secret()}}
        POSTGRES_PASSWORD = <32chars>      ← literal, no ${{secret()}}
[ ] 4. Agregar volumen: 1 GB mínimo, mount path /var/lib/postgresql/data
[ ] 5. Habilitar TCP Proxy en Settings del servicio Postgres
[ ] 6. Deploy del servicio Postgres
[ ] 7. Validar con psql desde Mac: SELECT current_user → debe decir "postgres"
[ ] 8. Crear servicio worker (Python)
[ ] 9. Agregar archivos: Procfile, runtime.txt, requirements.txt
[ ] 10. En Variables del worker:
         DATABASE_URL = ${{Postgres.DATABASE_URL}}
         ANTHROPIC_API_KEY = <valor manual>
         (demás variables de la app)
[ ] 11. Configurar pre-deploy command para migraciones
[ ] 12. Deploy del worker
[ ] 13. Verificar logs: scheduler arranca → pipeline corre → no errores de import
```

---

## 5. Errores que NO repetir

| Anti-patrón | Por qué es malo | Alternativa |
|-------------|-----------------|-------------|
| Editar `.env` manualmente con URL pública copiada del dashboard | Password se expone en historial, Railway la rota al verla | Usar `railway run` para inyectar variables, o pre-deploy commands |
| Usar `railway link` + `railway run` esperando que funcione como túnel | No es un túnel — solo inyecta variables en proceso local | Correr código que necesita DB interna directamente en Railway vía pre-deploy |
| Compartir/pegar contraseña en chat del agente | Password queda en historial de la sesión | Si se pegó por error, regenerar credenciales inmediatamente |
| Confiar en que el agente "ya configuró bien" sin validar | Los agentes pueden no tener visibilidad de Railway dashboard | Siempre verificar con psql o Railway SQL Editor después de cada cambio de config |
| Usar `${{secret()}}` para POSTGRES_USER o POSTGRES_PASSWORD | Genera credenciales rotativas que rompen TCP Proxy | Valores literales siempre para el usuario y password de Postgres |
| Intentar más de 3 veces el mismo fix cuando el proxy sigue fallando | Señal de bug estructural, no de configuración | Escalar a recrear el servicio o contactar soporte Railway |

---

## 6. Comandos de diagnóstico rápido

```bash
# Verificar conectividad TCP al proxy de Railway
nc -zv <host>.proxy.rlwy.net <puerto>

# Verificar si credenciales son estables (correr 3 veces, el username debe ser siempre "postgres")
railway run python3 -c "import os; print(os.environ.get('PGUSER','?'))"

# Ver todas las variables DB disponibles en el contexto de Railway (enmascaradas)
railway run python3 -c "
import os, re
for k,v in sorted(os.environ.items()):
    if any(x in k for x in ['DATABASE','POSTGRES','PG']):
        m = re.sub(r':([^:@]+)@', ':***@', v) if '@' in v else v
        print(f'{k}={m}')
"

# Probar conexión con asyncpg
railway run python3 -c "
import asyncio, asyncpg, os
async def t():
    conn = await asyncpg.connect(os.environ['DATABASE_PUBLIC_URL'], timeout=10)
    print(await conn.fetchval('SELECT current_user'))
    await conn.close()
asyncio.run(t())
"
```

---

*Documento creado a partir de 6 horas de debugging en sesión 22-23 abril 2026.*  
*Actualizar este documento si se descubren nuevos workarounds o bugs.*
