# Claude Outputs

Carpeta centralizada de outputs del sistema multi-agente.

## Estructura

```
claude_outputs/
├── integrator/   — outputs del integrador (revisiones pre-merge, reportes, decisiones)
├── claude-1/     — outputs de claude-1 (infra, pipeline, model-fields)
├── claude-2/     — outputs de claude-2 (scrapers, dashboard, dashboard-align)
└── claude-3/     — outputs de claude-3 (analyzer, metrics, metrics-align)
```

## Convención de nombres

```
OUTPUT_NNN_slug-descriptivo.md
```

- `NNN` — número secuencial con cero-padding (001, 002, 003…)
- `slug-descriptivo` — 3-5 palabras en kebab-case que identifiquen el contenido
- Cada carpeta tiene su propia secuencia independiente

**Ejemplos:**
```
integrator/OUTPUT_001_pre-merge-fase1.md
integrator/OUTPUT_002_merges-fase1-completados.md
integrator/OUTPUT_003_reporte-fase-a.md
claude-1/OUTPUT_001_hotfix-model-fields.md
claude-2/OUTPUT_001_hotfix-dashboard-align.md
```

## Cómo usarlo

1. Cuando un Claude termina una tarea, escribe su output en su carpeta con el siguiente número disponible
2. El integrador hace lo mismo en `integrator/`
3. Para alimentar el contexto a un Claude: copiar el contenido del `.md` relevante al chat
4. Los archivos son acumulativos — no se borran, se agregan

## Outputs existentes en el repo (pre-sistema)

Los siguientes reportes se generaron antes de crear este sistema y están en la raíz:

| Archivo | Contenido |
|---------|-----------|
| `REPORTE_FASE1.md` | Análisis pre-merge de las 3 ramas de Fase 1 |
| `REPORTE_FASE_A.md` | Análisis pre-merge de las 3 ramas de Fase A |
| `INCONSISTENCIA_DASHBOARD.md` | Divergencia stub vs modelo real, opciones A/B/C |
| `FASE_A.md` | Plan de trabajo Fase A (contrato de datos, criterios) |
