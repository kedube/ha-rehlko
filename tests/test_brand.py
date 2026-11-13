"""The brand images Home Assistant 2026.3+ shows for the integration have the right shapes."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

BRAND = Path(__file__).resolve().parent.parent / "custom_components" / "rehlko_energy" / "brand"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def png_header(path: Path) -> tuple[int, int, int]:
    """Width, height and colour type, read from the PNG's IHDR chunk."""
    data = path.read_bytes()
    assert data[:8] == PNG_SIGNATURE, f"{path.name} is not a PNG"
    assert data[12:16] == b"IHDR"
    width, height, _depth, colour_type = struct.unpack(">IIBB", data[16:26])
    return width, height, colour_type


def test_exactly_the_files_home_assistant_looks_for() -> None:
    assert sorted(path.name for path in BRAND.iterdir()) == sorted(
        f"{theme}{kind}{scale}.png"
        for theme in ("", "dark_")
        for kind in ("icon", "logo")
        for scale in ("", "@2x")
    )


@pytest.mark.parametrize("theme", ["", "dark_"])
@pytest.mark.parametrize(("scale", "size"), [("", 256), ("@2x", 512)])
def test_sizes_follow_home_assistants_rules(theme: str, scale: str, size: int) -> None:
    # Icons are square; logos keep the brand's proportions, landscape, shortest side as given.
    icon = png_header(BRAND / f"{theme}icon{scale}.png")
    assert icon[:2] == (size, size)
    width, height, colour_type = png_header(BRAND / f"{theme}logo{scale}.png")
    assert height == size
    assert width > 3 * height
    # Truecolour with alpha: the images must sit on any theme's background.
    assert icon[2] == colour_type == 6
