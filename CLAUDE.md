# Costco Operations Intelligence Monitor

Sistema de monitoreo de incidentes de alto impacto cerca de 3 sucursales Costco en Monterrey (Carretera Nacional, Cumbres, Valle Oriente). Detecta accidentes, incendios, balaceras, bloqueos e inundaciones en radio de 3km.

## Stack (obligatorio)
- Python 3.11+
- SQLAlchemy 2.x async + Alembic
- Pydantic v2 para todos los schemas
- FastAPI para la API
- Anthropic SDK directo (NO LangChain, NO OpenAI)
- structlog para logging
- pytest + pytest-asyncio para tests

## Principios de diseño
- Async/await por default donde haga sentido I/O
- Repository pattern para acceso a datos
- Dependency injection con FastAPI Depends
- Type hints estrictos — pasar mypy strict
- Sin imports circulares — si aparecen, arquitectura mal
- Nunca hardcodear API keys — todo vía Pydantic Settings

## Costcos monitoreados
- Carretera Nacional: 25.6026, -100.2640
- Cumbres: 25.7353, -100.4022
- Valle Oriente: 25.6457, -100.3072
