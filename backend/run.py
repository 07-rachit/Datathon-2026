import os
import uvicorn

if __name__ == "__main__":
    # Log ALL environment variables to diagnose what port Catalyst injects
    print("=== ENVIRONMENT VARIABLES ===")
    for key, val in sorted(os.environ.items()):
        if any(x in key.upper() for x in ["PORT", "ZOHO", "CATALYST", "ZC_"]):
            print(f"  {key} = {val}")
    print("=== END ENV VARS ===")

    port = (
        os.getenv("X_ZOHO_CATALYST_LISTEN_PORT")
        or os.getenv("X_ZC_PORT")
        or os.getenv("PORT")
        or "9000"
    )
    port = int(port)
    print(f"--> Binding to port {port}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, workers=1)
