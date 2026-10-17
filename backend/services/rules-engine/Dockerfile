FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY rules_service.py .

EXPOSE 8005

CMD ["python", "rules_service.py"]