#!/usr/bin/env python3
"""Build the integration's brand images from Rehlko's official logo files.

Home Assistant 2026.3 and later show the images in `custom_components/rehlko_energy/brand/`
as the integration's icon and logo. They are made from the horizontal logo that Rehlko
publishes on its Brand Portal (https://www.rehlko-downloadhub.com, Logos → Rehlko
Horizontal_primary → Raster): nothing is redrawn or recoloured, the artwork is only trimmed of
its transparent margin and scaled down.

    icon*.png       the symbol on its own, as Rehlko's own app and site icons use it
    logo*.png       the symbol and wordmark
    dark_*.png      the white version, for dark themes

Download these two files from the portal into one folder, then run (needs Pillow):

    rehlko-logo-horiz-midnight-blue-RGB.png
    rehlko-logo-horiz-white-RGB.png

    python3 scripts/build_brand_images.py <folder with the two PNGs>

Rehlko's name and logo are its trademarks. They identify the manufacturer whose generators
this unofficial integration works with, and are not covered by the repository's licence.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

BRAND = Path(__file__).resolve().parent.parent / "custom_components" / "rehlko_energy" / "brand"
SOURCES = {
    "": "rehlko-logo-horiz-midnight-blue-RGB.png",
    "dark_": "rehlko-logo-horiz-white-RGB.png",
}
# Home Assistant's sizes: icons are square, 256 px and 512 px (@2x); logos keep the brand's
# proportions with a shortest side of 128-256 px, and 256-512 px for @2x.
SIZES = {"": 256, "@2x": 512}


def trimmed(image: Image.Image) -> Image.Image:
    """`image` without its fully transparent margin."""
    return image.crop(image.getchannel("A").getbbox())


def symbol(logo: Image.Image) -> Image.Image:
    """The mark to the left of the wordmark: everything before the first empty column."""
    alpha = logo.getchannel("A")
    # A column's brightest pixel, not its average: the mark's rounded corners begin with
    # columns that are almost entirely transparent.
    gap = next(
        x for x in range(logo.width) if alpha.crop((x, 0, x + 1, logo.height)).getextrema()[1] == 0
    )
    mark = trimmed(logo.crop((0, 0, gap, logo.height)))
    side = max(mark.size)
    square = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    square.paste(mark, ((side - mark.width) // 2, (side - mark.height) // 2))
    return square


def save(image: Image.Image, height: int, name: str) -> None:
    width = round(image.width * height / image.height)
    image.resize((width, height), Image.Resampling.LANCZOS).save(BRAND / name, optimize=True)
    print(f"wrote brand/{name} ({width}x{height})")


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    BRAND.mkdir(exist_ok=True)
    for prefix, source in SOURCES.items():
        logo = trimmed(Image.open(Path(sys.argv[1]) / source).convert("RGBA"))
        for suffix, size in SIZES.items():
            save(symbol(logo), size, f"{prefix}icon{suffix}.png")
            save(logo, size, f"{prefix}logo{suffix}.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
