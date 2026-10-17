FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask==3.0.0 \
    requests \
    annoy==1.17.3 \
    sentence-transformers==2.5.1 \
    huggingface-hub==0.20.3 \
    psycopg2-binary==2.9.9 \
    numpy==1.24.3 \
    gunicorn==21.2.0 \
    pinecone

# Copy service code
COPY retrieval_service.py .

# Expose port
EXPOSE 8007

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8007/health')"

# Run with gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:8007", "--workers", "1", "--timeout", "300", "retrieval_service:app"]