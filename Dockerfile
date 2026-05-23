FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg)
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Expose the port provided by HF Spaces (default 7860)
EXPOSE $PORT

# Start the FastAPI app
CMD ["python", "app.py"]
