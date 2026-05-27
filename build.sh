#!/bin/bash
# Build Friday.app — a double-clickable macOS app — with PyInstaller.
#
# Friday is just the UI ("remote control"). The brain runs in the separate oMLX
# app, so install that and download a model FIRST (see README → Prerequisites).
# This script only packages Friday itself.
#
# Usage:  ./build.sh        then:  open dist/Friday.app
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "→ Creating virtualenv (.venv) ..."
  python3 -m venv .venv
fi

echo "→ Installing runtime deps + PyInstaller ..."
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt pyinstaller

echo "→ Cleaning previous build ..."
rm -rf build dist

echo "→ Building Friday.app ..."
.venv/bin/pyinstaller --noconfirm Friday.spec

# Ad-hoc sign so macOS (especially Apple Silicon) will launch the app locally
# without an Apple Developer account. Distributing it without Gatekeeper
# warnings would need real signing + notarization — out of scope here.
echo "→ Ad-hoc signing ..."
codesign --force --deep --sign - dist/Friday.app >/dev/null 2>&1 || true

echo ""
echo "✅ Built: dist/Friday.app"
echo "   Run:      open dist/Friday.app"
echo "   Install:  drag dist/Friday.app into /Applications"
echo ""
echo "⚠️  Friday needs the oMLX server running with the Qwen3.5-4B + whisper"
echo "    models installed. See README → Prerequisites."
