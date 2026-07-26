import os
import sys

# Add backend and current directory to sys.path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if os.path.exists(backend_path) and backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app.main import app

if __name__ == "__main__":
    target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")
    print(f"--> Launching full CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
