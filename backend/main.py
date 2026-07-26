import os
import sys
import glob

print("--> Catalyst AppSail Virtualenv Auto-Activator Starting...")

dir_path = os.path.dirname(os.path.abspath(__file__))
search_patterns = [
    os.path.join(dir_path, "*", "lib", "python*", "site-packages"),
    os.path.join(dir_path, "*", "*", "lib", "python*", "site-packages"),
    os.path.join(dir_path, "..", "*", "lib", "python*", "site-packages"),
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

if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

import uvicorn
from app.main import app

if __name__ == "__main__":
    target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")
    print(f"--> Starting CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
