"""
Script para ejecutar el monitoreo de forma continua.
"""

from main import NewsMonitor


def main():
    """Ejecuta el monitoreo de forma continua."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   Sistema de Monitoreo de Noticias de Alto Impacto               ║
║   Monterrey, Nuevo León - Radio 5 km Costco                      ║
║   MODO CONTINUO                                                   ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
    """)
    
    monitor = NewsMonitor()
    
    # Ejecutar de forma continua cada 15 minutos
    monitor.run_continuous(interval_minutes=15)


if __name__ == "__main__":
    main()

