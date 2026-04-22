#!/bin/bash
# Borra logs de corridas nocturnas más viejos que 14 días

LOG_DIR="/Users/mac/code/costco-v2/logs/nightly"

if [ -d "$LOG_DIR" ]; then
  find "$LOG_DIR" -name "run_*.log" -mtime +14 -delete
fi
