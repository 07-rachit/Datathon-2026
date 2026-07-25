import os
import uvicorn

if __name__ == "__main__":
    # Catalyst AppSail injects the port via X_ZC_PORT
    port = int(os.getenv("X_ZC_PORT") or os.getenv("PORT") or 8000)
    print(f"--> Starting AppSail Uvicorn server on port {port}...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1)
