import os
import sys

# 1. Vendor directory path for instant zero-dependency launch
vendor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
if not os.path.exists(vendor_dir):
    vendor_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "vendor")

if os.path.exists(vendor_dir) and vendor_dir not in sys.path:
    sys.path.insert(0, vendor_dir)

# 2. Backend directory path
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
if os.path.exists(backend_dir) and backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn
from app.main import app

if __name__ == "__main__":
    target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")
    print(f"--> Launching CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
