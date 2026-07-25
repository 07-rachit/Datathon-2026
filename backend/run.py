import os
import uvicorn

if __name__ == "__main__":
    # Catalyst AppSail may inject port via different env vars depending on version:
    # X_ZOHO_CATALYST_LISTEN_PORT (newer) or PORT (local serve uses 3001 by default)
    port = (
        os.getenv("X_ZOHO_CATALYST_LISTEN_PORT")
        or os.getenv("X_ZC_PORT")
        or os.getenv("PORT")
        or "9000"
    )
    port = int(port)
    print(f"--> Starting AppSail Uvicorn server on port {port}...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1)
