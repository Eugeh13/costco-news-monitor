"""
Configuración compartida de pytest para costco-news-monitor.

1. Pone la raíz del repo en sys.path para que `import app...` funcione
   sin instalar el paquete.
2. Bloquea conexiones de red reales en TODOS los tests (regla del proyecto:
   prohibido tocar red/BD/APIs de pago — todo va con mocks y datos sintéticos).
   Los mocks de unittest.mock no abren sockets, así que no se ven afectados.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture(autouse=True)
def _sin_red(monkeypatch):
    """Cualquier intento de conexión real de red falla de inmediato."""

    def _conexion_prohibida(*args, **kwargs):
        raise RuntimeError(
            "Los tests no deben tocar la red. Mockea la llamada externa."
        )

    monkeypatch.setattr(socket.socket, "connect", _conexion_prohibida)
    monkeypatch.setattr(socket, "create_connection", _conexion_prohibida)
