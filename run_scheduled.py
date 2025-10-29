"""
Script para ejecutar el monitoreo comenzando a las 11:30 AM y luego cada 30 minutos.
"""

import time
from datetime import datetime, timedelta
import os
import sys

# Agregar el directorio actual al path
sys.path.insert(0, '/home/ubuntu/news_monitor_app')

# Configurar credenciales de Telegram
os.environ['TELEGRAM_BOT_TOKEN'] = "7838511834:AAHWPOubGoq8Jo6KVWWr_AhTFJulB0oDlC0"
os.environ['TELEGRAM_CHAT_ID'] = "7510716093"

from main import NewsMonitor


def get_monterrey_time():
    """Obtiene la hora actual de Monterrey."""
    # Monterrey está en CST (UTC-6)
    import subprocess
    result = subprocess.run(['date', '+%H:%M:%S'], 
                          env={'TZ': 'America/Monterrey'}, 
                          capture_output=True, 
                          text=True)
    return result.stdout.strip()


def wait_until_1130():
    """Espera hasta las 11:30 AM hora de Monterrey."""
    print("╔═══════════════════════════════════════════════════════════════════╗")
    print("║   Sistema de Monitoreo - Costco MTY                              ║")
    print("║   Esperando hasta las 11:30 AM (hora Monterrey)                  ║")
    print("╚═══════════════════════════════════════════════════════════════════╝")
    print()
    
    while True:
        # Obtener hora actual de Monterrey
        import subprocess
        result = subprocess.run(['date', '+%H:%M'], 
                              env={'TZ': 'America/Monterrey'}, 
                              capture_output=True, 
                              text=True)
        current_time = result.stdout.strip()
        hour, minute = map(int, current_time.split(':'))
        
        print(f"⏰ Hora actual en Monterrey: {current_time}", end='\r')
        
        # Si ya pasaron las 11:30, empezar de inmediato
        if hour > 11 or (hour == 11 and minute >= 30):
            print(f"\n✓ Son las {current_time} - Iniciando monitoreo ahora...")
            break
        
        # Calcular tiempo de espera
        target_hour = 11
        target_minute = 30
        
        current_minutes = hour * 60 + minute
        target_minutes = target_hour * 60 + target_minute
        wait_minutes = target_minutes - current_minutes
        
        if wait_minutes > 0:
            print(f"\n⏳ Faltan {wait_minutes} minutos para las 11:30 AM...")
            time.sleep(60)  # Esperar 1 minuto
        else:
            break


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
║   ⏱️  Primer monitoreo: 11:30 AM                                  ║
║   🔄 Intervalo: 30 minutos                                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    # Esperar hasta las 11:30 AM
    wait_until_1130()
    
    print("\n" + "="*70)
    print("✓ Iniciando sistema de monitoreo")
    print("="*70 + "\n")
    
    # Crear instancia del monitor
    monitor = NewsMonitor()
    
    # Ejecutar continuamente cada 30 minutos
    monitor.run_continuous(interval_minutes=30)


if __name__ == "__main__":
    main()

