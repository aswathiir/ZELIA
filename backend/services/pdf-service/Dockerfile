FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8006

CMD ["uvicorn", "pdf_service:app", "--host", "0.0.0.0", "--port", "8006"]
