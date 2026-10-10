#!/bin/bash
# Builds "ROZ Hub.app" and copies it to /Applications so it shows in Launchpad and Spotlight.
# Pinning to the Dock is manual: open the app, right-click its Dock icon > Options > Keep in Dock.
set -euo pipefail
cd "$(dirname "$0")/../.."

python3 -m venv .build-venv
.build-venv/bin/pip install -q -r packaging/requirements-build.txt

# macOS icons must be .icns, built from an .iconset folder with one PNG per size.
# 256px is the largest source, so the 512pt sizes are upscaled.
mkdir -p .build/roz.iconset
for s in 16 32 128 256; do
  sips -z "$s" "$s" logo/roz-256.png --out ".build/roz.iconset/icon_${s}x${s}.png" >/dev/null
  sips -z "$((s*2))" "$((s*2))" logo/roz-256.png --out ".build/roz.iconset/icon_${s}x${s}@2x.png" >/dev/null
done
iconutil -c icns .build/roz.iconset -o .build/roz.icns

# --add-data uses ':' as the separator on macOS
.build-venv/bin/pyinstaller --noconfirm --windowed --name "ROZ Hub" \
    --icon .build/roz.icns \
    --osx-bundle-identifier com.republicofzani.rozhub \
    --add-data "$PWD/logo:logo" --add-data "$PWD/keyboard.json:." \
    --distpath dist --workpath .build/work --specpath .build \
    roz_he_configurator.py

rm -rf "/Applications/ROZ Hub.app"
cp -R "dist/ROZ Hub.app" /Applications/
echo "Installed. Open 'ROZ Hub' from Launchpad or Spotlight."
echo "First launch: the app is unsigned, so right-click it > Open to allow it."
