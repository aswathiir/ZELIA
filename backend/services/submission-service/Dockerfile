FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY certs /app/certs

EXPOSE 8004

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]
