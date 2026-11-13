#!/bin/bash
# Build docs/images/panel_phone.png, the picture at the top of the README: three phone-sized
# views of the panel, side by side on a transparent background. They are taken from the panel's
# local preview, so everything shown is simulated data.
#
#   cd frontend && npm run dev          # in another terminal; serves the preview on port 5173
#   scripts/build_readme_images.sh
#
# Needs Google Chrome; set CHROME to its binary if it is not in macOS's usual place. Look at
# the result before committing it: a view captured before its picture loaded has an empty frame.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/images/panel_phone.png"
PREVIEW="${PREVIEW:-http://127.0.0.1:5173/frontend/dev/index.html}"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"

# One phone per line: how far the page is scrolled, then the preview's options. In the phone
# layout the tab bar starts 833 px down while the generator is in standby.
VIEWS=(
  "0   state=Running"
  "809 state=Standby&tab=controls"
  "594 state=Standby&tab=activity"
)

curl --silent --fail --output /dev/null "$PREVIEW" || {
  echo "The preview is not running at $PREVIEW (see the top of this script)." >&2
  exit 1
}

page="$(mktemp -t rehlko-readme).html"
trap 'rm -f "$page"' EXIT
{
  cat <<'HTML'
<!doctype html>
<style>
  html, body { margin: 0; background: transparent; }
  body { display: flex; gap: 20px; }
  .phone { position: relative; width: 390px; height: 820px; overflow: hidden;
           border-radius: 46px; background: #111416; }
  /* A hairline around each screen, so its edge shows on a dark page too. */
  .phone::after { content: ""; position: absolute; inset: 0; border-radius: inherit;
                  border: 1.5px solid rgba(255, 255, 255, 0.2); pointer-events: none; }
  iframe { display: block; border: 0; width: 390px; height: 2600px; }
</style>
HTML
  for view in "${VIEWS[@]}"; do
    read -r scrolled options <<< "$view"
    echo "<div class=\"phone\"><iframe style=\"margin-top: -${scrolled}px\"" \
      "src=\"$PREVIEW?bar=0&narrow=1&theme=Dark&model=26RCA&$options\"></iframe></div>"
  done
} > "$page"

mkdir -p "$(dirname "$OUT")"
# Three 390 px phones and two 20 px gaps, at twice the size for sharp text.
"$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
  --window-size=1210,820 --default-background-color=00000000 --virtual-time-budget=10000 \
  --screenshot="$OUT" "file://$page" > /dev/null 2>&1
echo "wrote ${OUT#"$ROOT"/}"
