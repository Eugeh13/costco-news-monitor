#!/bin/bash

# Script para configurar cron para ejecutar el monitoreo cada 30 minutos
# comenzando a las 11:30 AM hora de Monterrey (CST = UTC-6)

echo "╔═══════════════════════════════════════════════════════════════════╗"
echo "║   Configurando Monitoreo Programado                              ║"
echo "║   Hora de Monterrey (CST/CDT)                                    ║"
echo "╚═══════════════════════════════════════════════════════════════════╝"
echo ""

# Monterrey usa CST (UTC-6) en invierno y CDT (UTC-5) en verano
# 11:30 AM CST = 17:30 UTC
# 11:30 AM CDT = 16:30 UTC

# Configurar para ambas posibilidades (cada 30 minutos desde las 11:30 AM Monterrey)
# En UTC esto es 17:30 (CST) o 16:30 (CDT)

# Opción: ejecutar a las 30 de cada hora desde las 11:30 AM hasta las 11:00 PM (hora Monterrey)
# Esto cubre 11:30, 12:00, 12:30, 13:00, 13:30, etc.

CRON_CMD="30 11-23 * * * cd /home/ubuntu/news_monitor_app && bash start_monitor.sh >> /home/ubuntu/news_monitor_app/cron.log 2>&1
0 12-23,0-11 * * * cd /home/ubuntu/news_monitor_app && bash start_monitor.sh >> /home/ubuntu/news_monitor_app/cron.log 2>&1"

# Limpiar cron jobs anteriores del monitor
crontab -l 2>/dev/null | grep -v "start_monitor.sh" | crontab -

# Agregar nuevos cron jobs
(crontab -l 2>/dev/null; echo "# Monitor Costco MTY - Cada 30 minutos desde 11:30 AM (hora Monterrey)") | crontab -
(crontab -l 2>/dev/null; echo "30 17-23 * * * cd /home/ubuntu/news_monitor_app && bash start_monitor.sh >> /home/ubuntu/news_monitor_app/cron.log 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "0 18-23,0-17 * * * cd /home/ubuntu/news_monitor_app && bash start_monitor.sh >> /home/ubuntu/news_monitor_app/cron.log 2>&1") | crontab -

echo "✓ Cron configurado para hora de Monterrey (CST = UTC-6)"
echo ""
echo "📅 Horario de ejecución:"
echo "  - Primera ejecución: 11:30 AM (hora Monterrey)"
echo "  - Luego cada 30 minutos: 12:00, 12:30, 13:00, 13:30, etc."
echo "  - Última ejecución del día: 11:00 PM"
echo ""
echo "🕐 Hora actual:"
date
echo ""
echo "📋 Cron jobs activos:"
crontab -l | grep -v "^#" | grep start_monitor
echo ""
echo "📄 Para ver el log:"
echo "  tail -f /home/ubuntu/news_monitor_app/cron.log"

