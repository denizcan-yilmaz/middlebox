#!/bin/bash

set -e

PY_MAIN="/code/python-processor/main.py"

if [ -f "$PY_MAIN" ]; then
    echo "[configure-processor] starting Python detector: $PY_MAIN"
    exec python3 "$PY_MAIN"
fi

echo "[configure-processor] WARNING: $PY_MAIN not found – sleeping forever"
exec sleep infinity