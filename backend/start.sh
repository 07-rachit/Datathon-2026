#!/bin/bash
PORT="${X_ZOHO_CATALYST_LISTEN_PORT:-9000}"
echo "--> Starting uvicorn on port $PORT"
exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
