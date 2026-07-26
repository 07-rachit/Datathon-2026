import os
import sys
import subprocess

# Auto-install requirements if any core dependency is missing
try:
    import uvicorn
    import fastapi
    import sqlalchemy
except ImportError:
    print("--> Auto-installing dependencies via pip...")
    req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if os.path.exists(req_file):
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", req_file], check=False)
    else:
        subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", "fastapi", "uvicorn[standard]", "sqlalchemy", "pydantic", "pydantic-settings", "python-jose[cryptography]", "passlib[bcrypt]", "python-multipart", "bcrypt", "email-validator", "reportlab", "scikit-learn", "numpy", "requests", "slowapi", "pandas", "alembic"], check=False)

# Ensure app package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app

if __name__ == "__main__":
    import uvicorn
    port_str = os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000"
    try:
        port = int(port_str)
    except ValueError:
        port = 9000
        
    print(f"--> Starting AppSail Uvicorn server on 0.0.0.0:{port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
