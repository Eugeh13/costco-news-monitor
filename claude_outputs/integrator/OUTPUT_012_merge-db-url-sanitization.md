# OUTPUT_012 — Merge fix/db-url-sanitization

**Fecha:** 22 abril 2026  
**Worker:** integrator  
**Rama mergeada:** `fix/db-url-sanitization`  
**Commit del worker (claude-1):** `9a330b5`  
**Merge commit:** `b73447d`  
**`git log origin/v2-rewrite --oneline -1`:** `b73447d merge: fix/db-url-sanitization (sanitize DATABASE_URL against invisible chars)`

---

## Qué se mergeó

- `scripts/fix_alembic_version_col.py` — sanitización de DATABASE_URL: `.strip()`, `.strip('"\'')`, `.lstrip('﻿​')` contra BOM y zero-width chars que Railway puede inyectar
- `claude_outputs/claude-1/OUTPUT_011_diagnostic-database-url.md` — diagnóstico previo
- `claude_outputs/claude-1/OUTPUT_012_fix-db-url-sanitization.md` — output del fix

## Tests

214/214 passed (sin regresiones)

## Auditoría GOVERNANCE.md

| Check | Resultado |
|-------|-----------|
| `git status` | `nothing to commit, working tree clean` ✓ |
| `git log origin/v2-rewrite..HEAD` | vacío ✓ |
| `fix_alembic_version_col.py` — sanitización en línea 14 | `.strip().strip('"\'').lstrip('﻿​')` ✓ |
| `claude_outputs/claude-1/OUTPUT_012` presente | ✓ |
