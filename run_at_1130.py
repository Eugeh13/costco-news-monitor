"""
Script para ejecutar el monitoreo comenzando a las 11:30 AM y luego cada 30 minutos.
"""

import time
from datetime import datetime
import subprocess
import os
import sys
import io

# Forzar salida sin buffer para que los logs se escriban inmediatamente
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, line_buffering=True)

# Configurar credenciales de Telegram
os.environ['TELEGRAM_BOT_TOKEN'] = "7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0"
os.environ['TELEGRAM_CHAT_ID'] = "7510716093"

# Agregar el directorio actual al path
sys.path.insert(0, '/home/ubuntu/news_monitor_app')

from main import NewsMonitor


def get_monterrey_time():
    """Obtiene la hora actual de Monterrey como datetime."""
    result = subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], 
                          env={'TZ': 'America/Monterrey'}, 
                          capture_output=True, 
                          text=True)
    time_str = result.stdout.strip()
    return datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')


def calculate_wait_time():
    """Calcula cuántos segundos esperar hasta la próxima ejecución."""
    current = get_monterrey_time()
    
    # Calcular próxima ejecución (11:30, 12:00, 12:30, etc.)
    if current.hour < 11 or (current.hour == 11 and current.minute < 30):
        target_hour, target_minute = 11, 30
    elif current.minute < 30:
        target_hour, target_minute = current.hour, 30
    else:
        target_hour, target_minute = (current.hour + 1) % 24, 0
    
    current_minutes = current.hour * 60 + current.minute
    target_minutes = target_hour * 60 + target_minute
    
    if target_minutes < current_minutes:
        wait_minutes = (24 * 60 - current_minutes) + target_minutes
    else:
        wait_minutes = target_minutes - current_minutes
    
    wait_seconds = wait_minutes * 60 - current.second
    
    return wait_seconds, target_hour, target_minute


def main():
    """Función principal."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   Sistema de Monitoreo de Noticias de Alto Impacto               ║
║   Monterrey, Nuevo León - Radio 5 km Costco                      ║
║                                                                   ║
║   📱 NOTIFICACIONES TELEGRAM ACTIVADAS                            ║
║   🤖 Bot: @monitorCostco_bot                                      ║
║   ⏱️  Primer monitoreo: 11:30 AM (hora Monterrey)                 ║
║   🔄 Intervalo: 30 minutos                                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Calcular tiempo de espera
    wait_seconds, target_hour, target_minute = calculate_wait_time()
    current = get_monterrey_time()
    
    print(f"⏰ Hora actual en Monterrey: {current.hour}:{current.minute:02d}:{current.second:02d}")
    print(f"🎯 Próxima ejecución: {target_hour}:{target_minute:02d}")
    print(f"⏳ Tiempo de espera: {wait_seconds // 60} minutos y {wait_seconds % 60} segundos")
    print()
    
    if wait_seconds > 0:
        print("⏳ Esperando...")
        time.sleep(wait_seconds)
    
    print("\n" + "="*70)
    print("✓ ¡Es hora! Iniciando sistema de monitoreo")
    print("="*70 + "\n")
    
    # Crear instancia del monitor
    monitor = NewsMonitor()
    
    # Ejecutar continuamente cada 30 minutos
    try:
        monitor.run_continuous(interval_minutes=30)
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema detenido por el usuario")


if __name__ == "__main__":
    main()

