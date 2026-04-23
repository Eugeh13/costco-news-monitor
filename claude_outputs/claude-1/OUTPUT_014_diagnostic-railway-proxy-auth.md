# OUTPUT_014 — Diagnóstico: Railway TCP Proxy rechaza autenticación (operativo, sin commits)

**Fecha:** 2026-04-22
**Worker:** claude-1
**Tipo:** Diagnóstico operativo — SIN commits (problema de infra Railway, no de código)
**Directorio:** `/Users/mac/code/costco-v2` (repo principal, no worktree)

---

## Objetivo

Lanzar el dashboard local (`src/dashboard/main.py`) apuntando a la PostgreSQL de Railway, para visualizar la data que el scheduler escribe en producción.

---

## Contexto previo

El fix `7a81a33` (OUTPUT_013) ya aplicó:
- `load_dotenv()` en `src/dashboard/database.py`
- Sanitización de URL (BOM, zero-width space, comillas)

El error original era `Could not parse SQLAlchemy URL` por ausencia de `load_dotenv()`. Ese bug fue resuelto. El nuevo bloqueo es de red/auth.

---

## Diagnóstico ejecutado — paso a paso

### Paso 1: Validación del .env local

```
LENGTH: 102
STARTS: 'postgresql+asyncpg://postgres:h4fcb0p7qu'
ENDS:   '@centerbeam.proxy.rlwy.net:55487/railway'
HAS :// True / HAS @: True / HAS +asyncpg: True
```

URL bien formada. El problema no era el formato.

### Paso 2: Prueba de conectividad TCP

```bash
nc -zv centerbeam.proxy.rlwy.net 55487
# → Connection succeeded
```

El host y puerto responden. El problema es exclusivamente de autenticación.

### Paso 3: Prueba con múltiples contraseñas

Probadas en orden (todas fallaron con `InvalidPasswordError`):

| Fuente | Resultado |
|--------|-----------|
| Contraseña original en `.env` | `InvalidPasswordError` |
| `DATABASE_PUBLIC_URL` del dashboard Railway (copiada) | `InvalidPasswordError` |
| `PGPASSWORD` del dashboard Railway (copiada) | `InvalidPasswordError` |
| `POSTGRES_PASSWORD` del dashboard Railway (copiada) | `InvalidPasswordError` |
| `railway run` → `DATABASE_PUBLIC_URL` (inyectada por CLI) | `InvalidPasswordError` |
| `railway run` → `PGPASSWORD` (inyectada por CLI) | `InvalidPasswordError` |
| `railway run` → `POSTGRES_PASSWORD` (inyectada por CLI) | `InvalidPasswordError` |
| `railway connect Postgres` (herramienta oficial Railway CLI) | `InvalidPasswordError` |

Probados con: asyncpg, psycopg2, psql — mismos resultados.
Probados con SSL: `require`, `prefer`, `False` — sin diferencia.

### Paso 4: Regeneración de credenciales en Railway

Eugenio ejecutó **Regenerate Credentials** en el servicio Postgres de Railway.
El deploy finalizó exitosamente.

**Hallazgo crítico post-regeneración:**
Cada llamada a `railway run` genera un USERNAME distinto en `DATABASE_PUBLIC_URL`:

```
Llamada 1: postgresql://idyuopbnugrkbycyhgublgfjysswaoji:***@centerbeam...
Llamada 2: postgresql://jpiqaunofhxbungxgpetgpvhjjgcvjwp:***@centerbeam...
Llamada 3: postgresql://lydscklzxvppsfjckbqndunjfwcqjbnw:***@centerbeam...
```

Railway genera credenciales **efímeras** en `DATABASE_PUBLIC_URL` — cambian por invocación y el proxy las rechaza antes de que asyncpg pueda usarlas.

### Paso 5: Análisis de variables disponibles

```
DATABASE_URL       → postgresql://...@postgres.railway.internal:5432/railway  ← INTERNO, no accesible desde Mac
DATABASE_PUBLIC_URL → postgresql://<usuario-efímero>:***@centerbeam.proxy.rlwy.net:55487/railway  ← rotativo, rechazado
PGPASSWORD         ≠ POSTGRES_PASSWORD  ← inconsistencia Railway
```

### Paso 6: Intento de resolución interna

```python
socket.getaddrinfo('postgres.railway.internal', 5432)
# → [Errno 8] nodename nor servname provided, or not known
```

`railway run` inyecta variables pero NO crea túnel de red local. La URL interna no es accesible desde Mac.

---

## Causa raíz identificada

El TCP Proxy de Railway (`centerbeam.proxy.rlwy.net:55487`) está generando credenciales efímeras por sesión que expiran o se invalidan antes de completar el handshake de autenticación PostgreSQL. Este comportamiento ocurre incluso con `railway connect Postgres` (herramienta oficial), lo que confirma que el problema es de configuración de Railway, no de nuestro código.

---

## Estado del código

**El código está correcto.** `src/dashboard/database.py` carga `.env`, sanitiza la URL y construye el engine correctamente. El error `Could not parse SQLAlchemy URL` original fue resuelto en OUTPUT_013.

---

## Próximo paso para Eugenio

El bloqueo actual requiere verificar la configuración del TCP Proxy en Railway:

1. Ve al servicio **Postgres** en Railway → pestaña **Connect**
2. Verifica el estado de **TCP Proxy** / **Public Networking**:
   - ¿Está activo o deshabilitado?
   - ¿El hostname mostrado es `centerbeam.proxy.rlwy.net`?
3. Si está activo: deshabilitar y re-habilitar el proxy (esto regenera el proxy, no los datos)
4. Si hay opción de **"Fixed Credentials"** o **"Static Credentials"**: activarla

Alternativa inmediata: usar el **SQL Editor** integrado de Railway (en el servicio Postgres → pestaña **Data** o **Query**) para verificar que hay datos en `decision_log` mientras se resuelve el acceso externo.

---

## Issues conocidos / pendientes

- TCP Proxy de Railway genera credenciales rotativas que no se aceptan → pendiente de diagnóstico en Railway dashboard
- `railway connect Postgres` también falla → confirma problema de Railway-side
- El código del dashboard está listo y correcto — en cuanto el proxy funcione, el dashboard arranca con un solo comando:

```bash
cd ~/code/costco-v2
python3 -m uvicorn src.dashboard.main:app --host 0.0.0.0 --port 8000
```
