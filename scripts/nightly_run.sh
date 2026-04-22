#!/bin/bash
# Corrida automática del pipeline costco-news-monitor
# Se ejecuta vía cron cada 2 horas entre 22:00 y 08:00

set -e
set -u

PROJECT_DIR="/Users/mac/code/costco-v2"
LOG_DIR="$PROJECT_DIR/logs/nightly"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/run_${TIMESTAMP}.log"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

# Cambiar al proyecto
cd "$PROJECT_DIR"

# Cargar variables de entorno
set -a
source .env
set +a

# Correr pipeline
echo "=== Nightly run starting at $(date) ===" >> "$LOG_FILE"
/usr/local/bin/python3 scripts/run_pipeline.py >> "$LOG_FILE" 2>&1
echo "=== Finished at $(date) ===" >> "$LOG_FILE"

echo "Run complete. Log: $LOG_FILE"
