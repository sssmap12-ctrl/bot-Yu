FROM python:3.11-slim

# Ensure writable cargo cache for Rust packages
ENV CARGO_HOME=/tmp/.cargo

WORKDIR /app

# Install system dependencies (ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
# Install dependencies without isolation to use pre‑built wheels when possible
RUN pip install --no-cache-dir --no-build-isolation -r requirements.txt

# Copy source code
COPY . .

# Expose the port provided by HF Spaces (default 7860)
EXPOSE $PORT

# Start the FastAPI app
CMD ["python", "app.py"]
