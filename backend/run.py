import os
import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "8000")
    print(f"--> Starting CrimeIntel FastAPI backend on http://127.0.0.1:{port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
