#!/bin/bash

# Script para iniciar el sistema de monitoreo con credenciales de Telegram

# Configurar credenciales de Telegram
export TELEGRAM_BOT_TOKEN="7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0"
export TELEGRAM_CHAT_ID="7510716093"

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║                                                                   ║"
echo "║   Sistema de Monitoreo de Noticias - Costco MTY                  ║"
echo "║   Iniciando con notificaciones de Telegram...                    ║"
echo "║                                                                   ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""
echo "✓ Bot: @monitorCostco_bot"
echo "✓ Intervalo: 30 minutos"
echo "✓ Radio: 5 km alrededor de Costcos en Monterrey"
echo ""

# Cambiar al directorio del proyecto
cd /home/ubuntu/news_monitor_app

# Ejecutar el sistema
python3.11 run_30min.py

