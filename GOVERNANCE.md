# GOVERNANCE.md — Protocolo de trabajo para todos los workers

**Propósito:** Evitar que trabajo valioso se pierda por falta de verificación.  
**Regla fundamental:** Si no está en origin, no existe. Un archivo en disco local del worker no es entregable hasta que `git push` confirme que llegó a GitHub.

---

## 1. Estructura de ramas

### Rama principal
- `v2-rewrite` — rama de desarrollo activa. Todo merge va aquí.

### Ramas de workers (prefijos obligatorios)
| Prefijo | Uso | Ejemplo |
|---------|-----|---------|
| `feat/` | Nueva funcionalidad | `feat/dashboard-filters` |
| `fix/` | Bug fix | `fix/dedup-false-positive` |
| `ops/` | Scripts de operación, cron, infra | `ops/nightly-cron` |
| `docs/` | Documentación, outputs, reportes | `docs/screenshots-folder` |
| `refactor/` | Refactor sin cambio de comportamiento | `refactor/classifier-cleanup` |
| `test/` | Solo tests | `test/geolocator-cases` |

### Convención de nombres de ramas semana/tipo
```
week{N}/{descripcion}        # ej: week2/api-and-tokens
{prefijo}/{descripcion}      # ej: ops/nightly-cron
```

---

## 2. Estructura de outputs

Todo worker debe dejar trazabilidad de su trabajo en:

```
claude_outputs/
├── integrator/   OUTPUT_NNN_slug.md
├── claude-1/     OUTPUT_NNN_slug.md
├── claude-2/     OUTPUT_NNN_slug.md
└── claude-3/     OUTPUT_NNN_slug.md
```

### Convención de nombres
```
OUTPUT_NNN_slug-descriptivo.md
```
- `NNN` — número secuencial con cero-padding, independiente por carpeta
- `slug-descriptivo` — 3-5 palabras kebab-case que identifican el contenido
- Nunca reutilizar un número aunque el archivo anterior se haya borrado

### Contenido mínimo de un OUTPUT
```markdown
# OUTPUT_NNN — Título descriptivo
**Fecha:** YYYY-MM-DD
**Worker:** claude-N / integrator
**Rama trabajada:** nombre-de-rama
**Commit(s):** hash1, hash2

## Qué se hizo
## Archivos creados/modificados
## Decisiones tomadas
## Issues conocidos o pendientes
```

---

## 3. Protocolo de 7 pasos — obligatorio para todo worker

### Paso 1: Arranque
```bash
git checkout v2-rewrite       # o la rama asignada
git pull origin v2-rewrite    # siempre partir de estado actualizado
git status                    # confirmar working tree clean
```
Si `git status` muestra cambios no esperados, **parar y reportar** antes de continuar.

### Paso 2: Trabajo
- Hacer solo lo que está en el contrato de la tarea
- Si surge algo fuera del alcance → BACKLOG.md, no al código
- Commits pequeños y atómicos mientras se trabaja

### Paso 3: Crear OUTPUT
Antes de hacer el commit final, escribir el OUTPUT en `claude_outputs/<mi-carpeta>/OUTPUT_NNN_slug.md`.  
El OUTPUT debe incluir el hash del commit (o dejarlo como pendiente si aún no se commitó).

### Paso 4: Verificación pre-commit
```bash
ls -la <archivos que deberían existir>   # confirmar que existen en disco
git status                               # ver exactamente qué va a entrar
git diff --stat                          # revisar qué cambió
```
**Si `git status` no muestra los archivos esperados → no continuar. Diagnosticar.**

### Paso 5: Commit
```bash
git add <archivos específicos>    # nunca git add . sin revisar
git commit -m "tipo: descripción concisa"
```
Verificar que el commit incluye exactamente lo esperado:
```bash
git show --stat HEAD
```

### Paso 6: Push con verificación
```bash
git push origin <rama>
git fetch origin
git log origin/<rama> --oneline -1    # confirmar que el hash llegó a origin
```
**Este es el paso que separa "hice el trabajo" de "el trabajo existe".**

### Paso 7: Reporte al chat
El reporte debe incluir:
- **Commit hash** (los primeros 7 caracteres mínimo)
- **Lista de archivos** creados/modificados
- **Confirmación explícita** de que `git log origin` muestra el commit
- **Issues conocidos** si los hay

❌ No reportar "listo" sin el hash y la confirmación de origin.

---

## 4. Protocolo del integrator — 5 checks post-merge

Después de cada merge (o conjunto de merges), el integrador debe ejecutar:

### Check 1: Working tree limpio
```bash
git status
# Esperado: "nothing to commit, working tree clean"
# Si hay untracked → investigar, no ignorar
```

### Check 2: Local == remote
```bash
git log origin/v2-rewrite..HEAD --oneline
# Esperado: output vacío
# Si hay commits → push pendiente, ejecutarlo
```

### Check 3: Ramas de workers mergeadas
```bash
git branch -r | grep -E "(week|feat|fix|ops|docs)"
# Verificar que las ramas que debían mergearse ya no tienen commits nuevos
```

### Check 4: Archivos críticos existen en origin
Para cada archivo que los workers mencionaron como entregable:
```bash
git show origin/v2-rewrite:<path/al/archivo>    # debe devolver contenido, no error
```

### Check 5: Outputs llegaron
```bash
ls claude_outputs/claude-1/
ls claude_outputs/claude-2/
ls claude_outputs/claude-3/
ls claude_outputs/integrator/
# Verificar que el último OUTPUT de cada worker está commiteado
```

---

## 5. Protocolo del usuario — cierre de sesión

Antes de cerrar tmux / terminal:

1. **Pedir al integrator** el reporte final del día con `git log --oneline -10`
2. **Verificar** que `git status` dice `nothing to commit, working tree clean`
3. **Confirmar** que `git log origin/v2-rewrite..HEAD` está vacío
4. **Solo entonces** cerrar tmux

Si hay duda: `git push origin v2-rewrite` es siempre seguro de correr.

---

## 6. Señales de alerta

Si cualquiera de estas condiciones ocurre, **parar y auditar** antes de continuar:

| Señal | Qué hacer |
|-------|-----------|
| Worker reporta "listo" sin dar commit hash | Pedir hash explícito, verificar en origin |
| `git status` muestra archivos untracked no esperados | Identificar qué son, commitear o ignorar según corresponda |
| Rama mencionada en origin/remote no tiene commits nuevos | El worker no hizo push — seguir up |
| Archivo mencionado en el reporte no aparece en `git show origin/v2-rewrite:<path>` | El archivo existe local pero no llegó a origin |
| Merge que "no tuvo conflictos" pero tampoco trajo archivos nuevos | Verificar que la rama source tenía commits antes del merge |
| `git log origin/v2-rewrite..HEAD` tiene commits | Hay trabajo local no pusheado |

---

## 7. Anti-patrones prohibidos

- ❌ `git add .` o `git add -A` sin revisar `git status` primero
- ❌ Reportar "listo" o "terminado" sin incluir el commit hash
- ❌ `git push` sin verificar con `git log origin/<rama> --oneline -1` que llegó
- ❌ Asumir que "crear un archivo" en la conversación de Claude guarda el archivo en disco del usuario — siempre verificar con `ls -la`
- ❌ Committear binarios grandes (imágenes > 1MB, `.db` files, videos)
- ❌ Trabajar directo en `main` sin pasar por `v2-rewrite`
- ❌ Hacer merge sin correr `pytest tests/ -x` cuando la rama toca código de producción
- ❌ Crear una rama nueva para trabajo que debería ir en `v2-rewrite` directo (docs, configs menores)

---

## 8. Historial de incidentes — Día 1 (20 abril 2026)

### Incidente 1: `scripts/nightly_run.sh` nunca llegó al repo
- **Worker:** claude-1 (rama `ops/nightly-cron`)
- **Qué pasó:** El script fue creado localmente pero el push no se verificó contra origin. El integrador asumió que estaba en la rama al hacer merge, pero la rama en origin estaba vacía o desactualizada.
- **Impacto:** Script de operación perdido, descubierto en limpieza final del día.
- **Fix aplicado:** Se re-creó el script y se commiteó directamente.
- **Lección:** Paso 6 (push con verificación de origin) es no-negociable.

### Incidente 2: `OUTPUT_003` y `OUTPUT_004` de claude-3 quedaron untracked
- **Worker:** claude-3
- **Qué pasó:** Los outputs fueron escritos en disco pero nunca se hizo `git add` + `git commit`. Quedaron como archivos untracked que `git status` mostraba pero no entraban a commits automáticos.
- **Impacto:** Trazabilidad perdida hasta la limpieza del Día 1.
- **Fix aplicado:** Commiteados manualmente por el integrador en limpieza final (`51e49e2`).
- **Lección:** El OUTPUT debe commitearse en el mismo commit que el trabajo, no como paso opcional posterior.

### Incidente 3: `COMMERCIAL_STRATEGY.md` se perdió
- **Worker:** desconocido (posiblemente claude-2 o claude-3)
- **Qué pasó:** El archivo fue mencionado en reportes como entregado, pero no se encontró en origin al hacer auditoría. No había commit hash asociado.
- **Impacto:** Documento de estrategia comercial perdido, requirió re-creación.
- **Fix aplicado:** Re-creado por worker y commiteado (`7bef08e docs: add commercial strategy for week 4 demo`).
- **Lección:** Si un reporte menciona un archivo, el integrador debe verificar con `git show origin/v2-rewrite:<path>` antes de dar el merge por cerrado.

---

*Creado: 21 abril 2026. Actualizar cuando ocurran nuevos incidentes o se refinen los protocolos.*
