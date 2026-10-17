FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8008

CMD ["uvicorn", "scraper_service:app", "--host", "0.0.0.0", "--port", "8008"]
