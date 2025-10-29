#!/usr/bin/env python3.11
"""
Script para ejecutar el monitoreo en horarios fijos (cada 30 minutos: :00 y :30)
VERSIÓN CON ANÁLISIS DE IA
"""

import time
from datetime import datetime, timedelta
from main_ai import NewsMonitorAI


def get_next_scheduled_time():
    """
    Calcula el próximo horario programado (:00 o :30).
    
    Returns:
        datetime: Próximo horario de ejecución
    """
    now = datetime.now()
    current_minute = now.minute
    
    # Si estamos antes del minuto 30, el próximo es :30
    if current_minute < 30:
        next_time = now.replace(minute=30, second=0, microsecond=0)
    else:
        # Si estamos en o después del minuto 30, el próximo es :00 de la siguiente hora
        next_time = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    
    return next_time


def wait_until_next_scheduled_time():
    """Espera hasta el próximo horario programado."""
    next_time = get_next_scheduled_time()
    now = datetime.now()
    wait_seconds = (next_time - now).total_seconds()
    
    print(f"⏰ Próxima ejecución programada: {next_time.strftime('%H:%M:%S')}")
    print(f"⏳ Esperando {int(wait_seconds)} segundos...\n")
    
    time.sleep(wait_seconds)


def main():
    """Función principal."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   Sistema de Monitoreo Automático - Horarios Fijos               ║
║   Ejecuta cada 30 minutos (:00 y :30)                            ║
║   Versión con Análisis de IA (OpenAI)                            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    print("🚀 Iniciando sistema de monitoreo automático con IA...")
    print("📅 Horarios de ejecución: cada hora en punto (:00) y media hora (:30)")
    print("🛑 Presiona Ctrl+C para detener\n")
    
    # Inicializar monitor con IA
    monitor = NewsMonitorAI(use_ai=True)
    
    try:
        while True:
            # Esperar hasta el próximo horario programado
            wait_until_next_scheduled_time()
            
            # Ejecutar monitoreo
            print(f"\n{'='*70}")
            print(f"🔔 EJECUCIÓN PROGRAMADA - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}\n")
            
            try:
                monitor.run_once()
            except Exception as e:
                print(f"\n⚠️  Error en la ejecución del monitoreo: {e}")
                print("   El sistema continuará en el próximo horario programado\n")
            
            print(f"\n{'='*70}")
            print(f"✓ Ejecución completada - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}\n")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Sistema detenido por el usuario")
        print("✓ Monitoreo automático finalizado\n")


if __name__ == "__main__":
    main()
