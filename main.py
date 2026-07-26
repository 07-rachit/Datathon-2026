import os
import sys

# Ensure backend directory and root are in import path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
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
