# OUTPUT_008 — Merge fix/alembic-version-col-width

**Fecha:** 22 abril 2026  
**Worker:** integrator  
**Rama mergeada:** `fix/alembic-version-col-width`  
**Commit del worker (claude-1):** `60f08e2`  
**Merge commit:** `2ae58ad`  
**`git log origin/v2-rewrite --oneline -1`:** `2ae58ad merge: fix/alembic-version-col-width (VARCHAR(32) fix for PostgreSQL alembic_version)`

---

## Qué se mergeó

- `scripts/fix_alembic_version_col.py` — script para ampliar VARCHAR(32)→VARCHAR(255) en tabla `alembic_version` de PostgreSQL. Permisos: `-rwxr-xr-x` ✓
- `claude_outputs/claude-1/OUTPUT_007_fix-alembic-version-col.md` — output de claude-1

## Tests

214/214 passed (sin regresiones)

## Auditoría GOVERNANCE.md

| Check | Resultado |
|-------|-----------|
| `git status` | `nothing to commit, working tree clean` ✓ |
| `git log origin/v2-rewrite..HEAD` | vacío ✓ |
| Merge commit en historial | `2ae58ad` ✓ |
| `scripts/fix_alembic_version_col.py` ejecutable | `-rwxr-xr-x` ✓ |
| `claude_outputs/claude-1/OUTPUT_007` presente | ✓ |
