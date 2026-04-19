"""Tests for src/analyzer/types.py — Pydantic v2 validation."""
import pytest
from datetime import datetime
from pydantic import ValidationError

from src.analyzer.types import (
    GeoLocation,
    IncidentClassification,
    IncidentInput,
    IncidentType,
)


def test_incident_input_minimal():
    inc = IncidentInput(title="Accidente", content="Choque en Constitución", source="Milenio")
    assert inc.title == "Accidente"
    assert inc.published_at is None
    assert inc.url is None


def test_incident_input_full():
    inc = IncidentInput(
        title="Balacera",
        content="Tiroteo en Valle Oriente",
        source="El Norte",
        published_at=datetime(2026, 4, 19, 14, 0),
        url="https://example.com/nota",
    )
    assert inc.url == "https://example.com/nota"
    assert inc.published_at.year == 2026


def test_incident_classification_valid():
    cls = IncidentClassification(
        incident_type=IncidentType.FIRE,
        severity=8,
        affects_operations=True,
        reasoning="Incendio a 500m",
        recommended_action="Activar protocolo de evacuación",
    )
    assert cls.incident_type == IncidentType.FIRE
    assert cls.severity == 8


def test_incident_classification_severity_bounds():
    with pytest.raises(ValidationError):
        IncidentClassification(
            incident_type=IncidentType.OTHER,
            severity=11,  # out of range
            affects_operations=False,
            reasoning="x",
            recommended_action="y",
        )
    with pytest.raises(ValidationError):
        IncidentClassification(
            incident_type=IncidentType.OTHER,
            severity=0,  # out of range
            affects_operations=False,
            reasoning="x",
            recommended_action="y",
        )


def test_geolocation_defaults():
    geo = GeoLocation(lat=25.6455, lon=-100.3255, address="Valle Oriente")
    assert geo.confidence == 1.0


def test_geolocation_confidence_bounds():
    with pytest.raises(ValidationError):
        GeoLocation(lat=0, lon=0, address="x", confidence=1.5)

    with pytest.raises(ValidationError):
        GeoLocation(lat=0, lon=0, address="x", confidence=-0.1)


def test_incident_type_enum_values():
    assert IncidentType.ACCIDENT.value == "accident"
    assert IncidentType.FIRE.value == "fire"
    assert IncidentType.SHOOTING.value == "shooting"
    assert IncidentType.ROADBLOCK.value == "roadblock"
    assert IncidentType.FLOOD.value == "flood"
    assert IncidentType.OTHER.value == "other"
