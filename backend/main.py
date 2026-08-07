import os
import uvicorn
from app.main import app

if __name__ == "__main__":
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")
    print(f"--> Starting FastAPI Uvicorn Server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
