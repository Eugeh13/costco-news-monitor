"""
Scrapers package — exports all scrapers and the ALL_SCRAPERS registry.
"""

from src.scrapers.base import BaseScraper, RawArticle
from src.scrapers.milenio import MilenioScraper
from src.scrapers.info7 import Info7Scraper
from src.scrapers.horizonte import HorizonteScraper
from src.scrapers.proteccion_civil import ProteccionCivilScraper
from src.scrapers.bomberos_nl import BomberosNLScraper

ALL_SCRAPERS: list[BaseScraper] = [
    MilenioScraper(),
    Info7Scraper(),
    HorizonteScraper(),
    ProteccionCivilScraper(),
    BomberosNLScraper(),
]

__all__ = [
    "BaseScraper",
    "RawArticle",
    "MilenioScraper",
    "Info7Scraper",
    "HorizonteScraper",
    "ProteccionCivilScraper",
    "BomberosNLScraper",
    "ALL_SCRAPERS",
]
