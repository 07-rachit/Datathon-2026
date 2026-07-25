import os
import uvicorn

if __name__ == "__main__":
    # Catalyst AppSail injects port via X_ZOHO_CATALYST_LISTEN_PORT (default 9000)
    port = int(os.getenv("X_ZOHO_CATALYST_LISTEN_PORT") or os.getenv("PORT") or "9000")
    print(f"--> Starting on port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1)
