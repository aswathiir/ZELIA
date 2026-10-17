FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8013
CMD ["gunicorn", "--bind", "0.0.0.0:8013", "--workers", "1", "--timeout", "300", "form_filler_service:app"]
