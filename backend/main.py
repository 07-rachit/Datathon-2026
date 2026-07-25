import os
from app.main import app

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or 9000)
    print(f"--> Starting CrimeIntel API on port {port}...")
    uvicorn.run("main:app", host="0.0.0.0", port=port)
