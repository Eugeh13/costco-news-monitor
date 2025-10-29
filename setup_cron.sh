#!/bin/bash

# Script para configurar cron para ejecutar el monitoreo cada 30 minutos
# comenzando a las 11:30 AM

echo "Configurando cron para monitoreo cada 30 minutos desde las 11:30 AM..."

# Crear el comando cron
CRON_CMD="30,0 * * * * cd /home/ubuntu/news_monitor_app && bash start_monitor.sh >> /home/ubuntu/news_monitor_app/cron.log 2>&1"

# Agregar a crontab
(crontab -l 2>/dev/null | grep -v "start_monitor.sh"; echo "$CRON_CMD") | crontab -

echo "✓ Cron configurado"
echo ""
echo "El sistema se ejecutará:"
echo "  - Primera vez: Hoy a las 11:30 AM"
echo "  - Luego cada 30 minutos: 12:00, 12:30, 13:00, 13:30, etc."
echo ""
echo "Para ver los cron jobs activos:"
echo "  crontab -l"
echo ""
echo "Para ver el log:"
echo "  tail -f /home/ubuntu/news_monitor_app/cron.log"

