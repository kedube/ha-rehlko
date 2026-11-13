"""Translations: every key the code references exists, and every language stays in step."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "rehlko_energy"
PANEL_LOCALES = ROOT / "frontend" / "src" / "locales"
STRINGS = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
TRANSLATIONS = sorted((COMPONENT / "translations").glob("*.json"))
PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def leaves(tree: dict[str, Any], path: tuple[str, ...] = ()) -> Iterator[tuple[str, str]]:
    for key, value in tree.items():
        if isinstance(value, dict):
            yield from leaves(value, (*path, key))
        else:
            yield ".".join((*path, key)), value


ENGLISH = dict(leaves(STRINGS))


def test_strings_and_en_translation_match() -> None:
    en = json.loads((COMPONENT / "translations" / "en.json").read_text(encoding="utf-8"))
    assert en == STRINGS


def test_generated_files_are_current_and_catalogues_valid() -> None:
    """The build script regenerates nothing and finds nothing wrong (this is the CI check)."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_translations.py"), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_ships_the_expected_languages() -> None:
    assert {path.stem for path in TRANSLATIONS} == {
        "de",
        "en",
        "es",
        "fr",
        "it",
        "ja",
        "nl",
        "pl",
        "pt-BR",
        "zh-Hans",
    }


@pytest.mark.parametrize("path", TRANSLATIONS, ids=lambda path: path.stem)
def test_translation_fits_the_english(path: Path) -> None:
    """Only keys English has, with the same placeholders — Home Assistant drops the rest."""
    translated = dict(leaves(json.loads(path.read_text(encoding="utf-8"))))
    for key, text in translated.items():
        assert key in ENGLISH, f"{path.name}: {key} is not a translation key"
        assert text and text == text.strip(), f"{path.name}: {key} is empty or padded"
        assert sorted(PLACEHOLDER.findall(text)) == sorted(PLACEHOLDER.findall(ENGLISH[key])), (
            f"{path.name}: {key} placeholders differ"
        )
    # A gap falls back to English, but a mostly-empty file means a broken catalogue.
    assert len(translated) >= 0.95 * len(ENGLISH), f"{path.name} is missing most translations"


@pytest.mark.parametrize("path", [COMPONENT / "strings.json", *TRANSLATIONS], ids=lambda p: p.stem)
def test_states_attributes_and_units_have_no_placeholders(path: Path) -> None:
    """hassfest: "placeholders are not supported in this value"."""
    where = re.compile(r"entity\.[^.]+\.[^.]+\.(state\.|state_attributes\.|unit_of_measurement$)")
    tree = json.loads(path.read_text(encoding="utf-8"))
    offenders = {key: text for key, text in leaves(tree) if where.match(key) and "{" in text}
    assert not offenders


def test_services_yaml_matches_strings_and_module() -> None:
    import ast

    import yaml

    services_yaml = yaml.safe_load((COMPONENT / "services.yaml").read_text())
    assert set(services_yaml) == set(STRINGS["services"])
    # Every service's SCHEMAS entry lines up with strings.json and services.yaml.
    tree = ast.parse((COMPONENT / "services.py").read_text())
    schema_keys = set()
    for node in ast.walk(tree):
        target = None
        if isinstance(node, ast.Assign):
            target = next((t for t in node.targets if getattr(t, "id", "") == "SCHEMAS"), None)
        elif isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == "SCHEMAS":
            target = node.target
        if target is not None and isinstance(node.value, ast.Dict):
            schema_keys = {k.value for k in node.value.keys}
    assert schema_keys == set(STRINGS["services"])
    # Every field has a name and description, and every translated selector has its options.
    for service, definition in services_yaml.items():
        for field, spec in (definition.get("fields") or {}).items():
            assert field in STRINGS["services"][service]["fields"], f"{service}.{field}"
            select = (spec.get("selector") or {}).get("select") or {}
            if "translation_key" in select:
                options = STRINGS["selector"][select["translation_key"]]["options"]
                assert set(select["options"]) == set(options), f"{service}.{field}"


@pytest.mark.parametrize(
    "platform",
    [
        "sensor",
        "binary_sensor",
        "button",
        "select",
        "switch",
        "event",
        "number",
        "text",
        "datetime",
        "calendar",
        "update",
    ],
)
def test_entity_translation_keys_exist(platform: str) -> None:
    """translation_key="..." literals in each platform must exist under entity.<platform>."""
    source = (COMPONENT / f"{platform}.py").read_text()
    # Not the exceptions' keys, which follow `translation_domain=DOMAIN, `.
    keys = set(re.findall(r'(?<!DOMAIN, )translation_key="([a-z0-9_]+)"', source))
    keys |= set(re.findall(r'_attr_translation_key = "([a-z0-9_]+)"', source))
    assert keys, f"{platform}: no translation keys found"
    missing = keys - set(STRINGS["entity"].get(platform, {}))
    assert not missing, f"{platform}: missing translation keys {missing}"


def test_exception_keys_exist() -> None:
    """Every translated exception the code raises has a message."""
    used = set()
    for path in COMPONENT.rglob("*.py"):
        source = path.read_text()
        used |= set(
            re.findall(
                r'translation_domain=DOMAIN,\s*translation_key="([a-z_]+)"', source, re.DOTALL
            )
        )
    assert used, "no translated exceptions found"
    assert used <= set(STRINGS["exceptions"]), used - set(STRINGS["exceptions"])
    assert set(STRINGS["exceptions"]) <= used, "unused exception messages"


def test_server_rendered_texts_are_published() -> None:
    """texts.py's defaults are the English under the paths the entities read them from."""
    from custom_components.rehlko_energy import texts

    for path, defaults in (
        (texts.CALENDAR_SUMMARY_PATH, texts.CALENDAR_SUMMARY),
        (texts.CALENDAR_DESCRIPTION_PATH, texts.CALENDAR_DESCRIPTION),
        (texts.FIRMWARE_SUMMARY_PATH, texts.FIRMWARE_SUMMARY),
    ):
        for key, value in defaults.items():
            assert ENGLISH[f"entity.{path}.{key}"] == value
    assert f"entity.{texts.EXERCISE_MODE_PATH}.unloaded" in ENGLISH


def test_icons_cover_platforms() -> None:
    icons = json.loads((COMPONENT / "icons.json").read_text())
    assert "sensor" in icons["entity"]
    assert set(icons["services"]) == set(STRINGS["services"])
    # An icon for a translation key that does not exist is a typo.
    for platform, entries in icons["entity"].items():
        assert set(entries) <= set(STRINGS["entity"][platform]), platform


def test_sidebar_title_follows_the_panel_translations() -> None:
    from custom_components.rehlko_energy.sidebar import TITLES, sidebar_title

    assert set(TITLES) == {path.stem for path in TRANSLATIONS}
    for language, title in TITLES.items():
        panel = json.loads((PANEL_LOCALES / f"{language}.json").read_text(encoding="utf-8"))
        assert title == panel["common.generator"], language
    assert sidebar_title("es-419") == TITLES["es"]
    assert sidebar_title("pt") == TITLES["pt-BR"]
    assert sidebar_title("zh-Hans") == TITLES["zh-Hans"]
    assert sidebar_title("zh-Hant") == TITLES["en"]
    assert sidebar_title("tlh") == TITLES["en"]
    assert sidebar_title(None) == TITLES["en"]
