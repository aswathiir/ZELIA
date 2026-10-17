FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ultravox_proxy.py .

EXPOSE 8010

CMD ["python", "ultravox_proxy.py"]