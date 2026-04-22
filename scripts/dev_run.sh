#!/bin/bash
# Corrida manual del pipeline para desarrollo
# Uso: ./scripts/dev_run.sh

set -e
set -u

PROJECT_DIR="/Users/mac/code/costco-v2"
cd "$PROJECT_DIR"

# Cargar .env
set -a
source .env
set +a

echo "=== Pipeline starting at $(date) ==="
/usr/local/bin/python3 scripts/run_pipeline.py

# Resumen al final
echo ""
echo "=== DB state ==="
sqlite3 costco_motor.db <<SQL
SELECT 'Total records: ' || COUNT(*) FROM decision_log;
SELECT 'Records last 10 min: ' || COUNT(*)
FROM decision_log
WHERE created_at > datetime('now', '-10 minutes');
SELECT 'Cost last 10 min (USD): ' || ROUND(SUM(cost_estimated_usd), 4)
FROM decision_log
WHERE created_at > datetime('now', '-10 minutes');
SQL
