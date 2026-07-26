import os
import sys

dir_path = os.path.dirname(os.path.abspath(__file__))
if dir_path not in sys.path:
    sys.path.insert(0, dir_path)

import uvicorn
from app.main import app

if __name__ == "__main__":
    target_port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")
    print(f"--> Launching full CrimeIntel FastAPI App on 0.0.0.0:{target_port}...")
    uvicorn.run(app, host="0.0.0.0", port=target_port)
