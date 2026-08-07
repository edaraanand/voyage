FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

# OpenTelemetry Collector endpoint inside Kubernetes
# ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector-opentelemetry-collector.monitoring.svc.cluster.local:4318
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318

ENV LOG_LEVEL=INFO

EXPOSE 5003

CMD ["gunicorn", "--bind", "0.0.0.0:5003", "--workers", "2", "--threads", "4", "app:app"]
