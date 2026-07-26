import os
import sys
import subprocess

# Auto-install lightweight requirements if missing in container
try:
    import uvicorn
    import fastapi
except ImportError:
    print("--> Container auto-installing requirements.txt...")
    req_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if os.path.exists(req_path):
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", req_path])
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "fastapi", "uvicorn[standard]", "sqlalchemy", "pydantic", "pydantic-settings", "python-jose[cryptography]", "passlib", "python-multipart", "bcrypt<4.0.0", "email-validator", "slowapi"])

dir_path = os.path.dirname(os.path.abspath(__file__))
backend_path = os.path.join(dir_path, "backend")
if os.path.exists(backend_path) and backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

import uvicorn
from app.main import app

if __name__ == "__main__":
    target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")
    print(f"--> Starting CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
