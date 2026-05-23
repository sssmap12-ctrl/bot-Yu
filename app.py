import os
from uvicorn import run
from api.main import app

if __name__ == "__main__":
    # Hugging Face provides the PORT env var; default to 7860 for local testing
    port = int(os.getenv("PORT", "7860"))
    run(app, host="0.0.0.0", port=port)
