FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector-opentelemetry-collector.monitoring.svc.cluster.local:4318
ENV LOG_LEVEL=INFO
ENV GUNICORN_WORKERS=4
ENV GUNICORN_THREADS=8
ENV MAX_CONCURRENT_REQUESTS=8
ENV GUNICORN_TIMEOUT=15
EXPOSE 5000
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:5000 --worker-class gthread --workers ${GUNICORN_WORKERS} --threads ${GUNICORN_THREADS} --timeout ${GUNICORN_TIMEOUT} app:app"]
