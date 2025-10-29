#!/usr/bin/env python3.11
"""
Script para ejecutar el monitoreo en horarios fijos cada 30 minutos.
Ejecuta a las :00 y :30 de cada hora.
"""

import sys
import time
from datetime import datetime, timedelta
import pytz
import subprocess

# Zona horaria de Monterrey
MONTERREY_TZ = pytz.timezone('America/Monterrey')

def get_next_scheduled_time():
    """
    Calcula el próximo horario programado (:00 o :30).
    """
    now = datetime.now(MONTERREY_TZ)
    
    # Si estamos antes de los 30 minutos, programar para :30
    if now.minute < 30:
        next_time = now.replace(minute=30, second=0, microsecond=0)
    # Si estamos después de los 30 minutos, programar para la siguiente hora :00
    else:
        next_time = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    
    return next_time

def wait_until_next_schedule():
    """
    Espera hasta el próximo horario programado.
    """
    now = datetime.now(MONTERREY_TZ)
    next_time = get_next_scheduled_time()
    wait_seconds = (next_time - now).total_seconds()
    
    print(f"⏰ Hora actual en Monterrey: {now.strftime('%H:%M:%S')}")
    print(f"🎯 Próxima ejecución: {next_time.strftime('%H:%M')}")
    print(f"⏳ Tiempo de espera: {int(wait_seconds // 60)} minutos y {int(wait_seconds % 60)} segundos")
    print("⏳ Esperando...")
    
    time.sleep(wait_seconds)

def run_monitor():
    """
    Ejecuta el monitoreo.
    """
    print("=" * 70)
    print("✓ ¡Es hora! Iniciando sistema de monitoreo")
    print("=" * 70)
    
    # Ejecutar el script principal
    result = subprocess.run(
        [sys.executable, "main.py"],
        capture_output=False,
        text=True
    )
    
    return result.returncode == 0

def main():
    """
    Función principal que ejecuta el monitoreo en horarios fijos.
    """
    print("╔" + "=" * 67 + "╗")
    print("║" + " " * 67 + "║")
    print("║   Sistema de Monitoreo de Noticias de Alto Impacto               ║")
    print("║   Monterrey, Nuevo León - Radio 3 km Costco                      ║")
    print("║                                                                   ║")
    print("║   📱 NOTIFICACIONES TELEGRAM ACTIVADAS                            ║")
    print("║   🤖 Bot: @monitorCostco_bot                                      ║")
    print("║   ⏱️  Horarios: :00 y :30 de cada hora                            ║")
    print("║   🔄 Intervalo: 30 minutos                                        ║")
    print("║                                                                   ║")
    print("╚" + "=" * 67 + "╝")
    print()
    
    # Bucle infinito
    while True:
        try:
            # Esperar hasta el próximo horario programado
            wait_until_next_schedule()
            
            # Ejecutar el monitoreo
            success = run_monitor()
            
            if not success:
                print("⚠️  El monitoreo terminó con errores")
            
            # Pequeña pausa antes de calcular el siguiente horario
            time.sleep(2)
            
        except KeyboardInterrupt:
            print("\n\n✓ Sistema detenido por el usuario")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")
            print("⏳ Esperando 5 minutos antes de reintentar...")
            time.sleep(300)

if __name__ == "__main__":
    main()

