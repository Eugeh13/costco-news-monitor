"""Shared pytest fixtures and path setup."""
import sys
from pathlib import Path

# Ensure project root is on sys.path so `src` is importable
sys.path.insert(0, str(Path(__file__).parent.parent))
