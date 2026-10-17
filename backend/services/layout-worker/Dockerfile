FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Install CPU-only torch first (smaller download)
# Install torch (standard PyPI has aarch64 wheels)
ENV PIP_DEFAULT_TIMEOUT=1200
RUN pip install torch==2.3.0 --no-cache-dir

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Models will be downloaded at first startup and cached in the volume

EXPOSE 8003

CMD ["python", "layout_service.py"]
