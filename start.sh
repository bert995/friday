#!/bin/bash
# Launch Friday. Requires: oMLX server running + `python3 -m venv .venv &&
# .venv/bin/pip install -r requirements.txt` done once.
cd "$(dirname "$0")"
exec .venv/bin/python -m pet.shell
