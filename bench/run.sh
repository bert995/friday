#!/bin/bash
# Run the bake-off through oMLX's bundled Python (ships mlx + mlx_lm).
# This is a dev-only tool; the shipped app does NOT depend on mlx_lm.
set -euo pipefail
CONTENTS=/Applications/oMLX.app/Contents
LAYERS="$CONTENTS/Python"
export PYTHONHOME="$LAYERS/cpython-3.11"
export PYTHONPATH="$CONTENTS/Resources:$LAYERS/app-omlx-app/lib/python3.11/site-packages:$LAYERS/framework-mlx-framework/lib/python3.11/site-packages"
export PYTHONDONTWRITEBYTECODE=1
exec "$CONTENTS/MacOS/python3" "$(dirname "$0")/run.py" "$@"
