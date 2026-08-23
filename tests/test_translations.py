"""Translations are shipped files, so nothing resolves them for us."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

COMPONENT = Path(__file__).parent.parent / "custom_components" / "kaco"
STRINGS = COMPONENT / "strings.json"
TRANSLATIONS = sorted((COMPONENT / "translations").glob("*.json"))


def keys(obj: dict, prefix: str = "") -> set[str]:
    """Every key path in a nested dict."""
    found: set[str] = set()
    for key, value in obj.items():
        path = f"{prefix}.{key}" if prefix else key
        found.add(path)
        if isinstance(value, dict):
            found |= keys(value, path)
    return found


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_translations_exist() -> None:
    """Home Assistant reads translations/, not strings.json."""
    assert TRANSLATIONS, "no translation files"
    assert (COMPONENT / "translations" / "en.json").exists()


@pytest.mark.parametrize("path", TRANSLATIONS, ids=lambda p: p.stem)
def test_translation_is_complete(path: Path) -> None:
    """Every key in strings.json is translated, and none are invented."""
    expected = keys(load(STRINGS))
    actual = keys(load(path))

    assert not expected - actual, f"{path.name} is missing {sorted(expected - actual)}"
    assert not actual - expected, f"{path.name} has unknown {sorted(actual - expected)}"


@pytest.mark.parametrize("path", [STRINGS, *TRANSLATIONS], ids=lambda p: p.stem)
def test_no_unresolved_key_references(path: Path) -> None:
    """``[%key:...%]`` is resolved by core's translation build.

    A custom integration never goes through it, so a reference would be shown
    to the user verbatim.
    """
    assert "[%key:" not in path.read_text(encoding="utf-8")


def test_every_entity_translation_key_is_defined() -> None:
    """A translation_key with no entry renders as a raw slug in the UI."""
    from custom_components.kaco import number, select, sensor, switch

    defined = load(STRINGS)["entity"]
    used: set[tuple[str, str]] = set()

    for platform, descriptions in (
        (
            "sensor",
            (
                *sensor.SENSORS,
                *sensor.PHASE_SENSORS,
                *sensor.CURRENT_SENSORS,
                sensor.ENERGY,
                *sensor.DIAGNOSTICS,
            ),
        ),
        ("number", number.NUMBERS),
        ("switch", switch.SWITCHES),
        ("select", (select.DESCRIPTION,)),
    ):
        for description in descriptions:
            assert description.translation_key is not None, description.key
            used.add((platform, description.translation_key))

    # The per-string sensors are built at runtime from the discovered count.
    for description in sensor._string_sensors(1):
        used.add(("sensor", description.translation_key))

    missing = [f"{p}.{k}" for p, k in sorted(used) if k not in defined.get(p, {})]
    assert not missing, f"undefined translation keys: {missing}"
