"""
Script para ejecutar el monitoreo cada 30 minutos de forma continua.
Configurado para enviar notificaciones SMS al número +52 8124686732
"""

from main import NewsMonitor


def main():
    """Ejecuta el monitoreo cada 30 minutos."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   Sistema de Monitoreo de Noticias de Alto Impacto               ║
║   Monterrey, Nuevo León - Radio 5 km Costco                      ║
║                                                                   ║
║   📱 NOTIFICACIONES SMS ACTIVADAS                                 ║
║   📞 Número: +52 8124686732                                       ║
║   ⏱️  Intervalo: 30 minutos                                       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    monitor = NewsMonitor()
    
    # Ejecutar de forma continua cada 30 minutos
    monitor.run_continuous(interval_minutes=30)


if __name__ == "__main__":
    main()

