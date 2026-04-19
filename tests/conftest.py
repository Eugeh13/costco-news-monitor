"""Shared pytest fixtures and path setup."""
import sys
from pathlib import Path

import structlog

# Ensure project root is on sys.path so `src` is importable
sys.path.insert(0, str(Path(__file__).parent.parent))


def pytest_configure(config: object) -> None:
    """Route structlog through stdlib logging so pytest caplog can capture output."""
    structlog.configure(
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
