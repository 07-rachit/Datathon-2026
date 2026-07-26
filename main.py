import os
import sys
import glob

print("--> Catalyst AppSail Virtualenv Auto-Activator Starting...")

# 1. Search and add all virtual environment site-packages to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
search_patterns = [
    os.path.join(root_dir, "*", "lib", "python*", "site-packages"),
    os.path.join(root_dir, "*", "*", "lib", "python*", "site-packages"),
    os.path.join(root_dir, "backend", "*", "lib", "python*", "site-packages"),
    "/catalyst/*/lib/python*/site-packages",
    "/catalyst/*/*/lib/python*/site-packages",
    "/app/*/lib/python*/site-packages",
    "/app/*/*/lib/python*/site-packages",
    "/tmp/*/lib/python*/site-packages"
]

for pat in search_patterns:
    for p in glob.glob(pat):
        if p not in sys.path:
            print(f"--> Discovered Virtualenv site-packages: {p}")
            sys.path.insert(0, p)

# 2. Add backend and root to sys.path
backend_path = os.path.join(root_dir, "backend")
if os.path.exists(backend_path) and backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import uvicorn
from app.main import app

if __name__ == "__main__":
    target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")
    print(f"--> Starting CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
