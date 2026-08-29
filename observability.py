import logging
import os
import threading
from contextvars import ContextVar

from opentelemetry import metrics, trace
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

SERVICE_NAME = "voyage-matcher-k8s"

OTEL_COLLECTOR = os.getenv(
    "OTEL_COLLECTOR_ENDPOINT",
    "http://otel-collector-opentelemetry-collector.monitoring.svc.cluster.local:4318",
)

request_id_ctx = ContextVar(
    "request_id",
    default="unknown",
)

resource = Resource.create(
    {
        "service.name": SERVICE_NAME,
        "service.version": "1.0.0",
        "deployment.environment": "dev",
    }
)


class OtelContextFilter(logging.Filter):
    def filter(self, record):
        if not hasattr(record, "otelTraceID"):
            record.otelTraceID = "0"
        if not hasattr(record, "otelSpanID"):
            record.otelSpanID = "0"
        record.request_id = request_id_ctx.get()
        record.service_name = SERVICE_NAME

        # Defaults for optional fields
        record.query_id = getattr(record, "query_id", "-")
        record.client_wait_ms = getattr(record, "client_wait_ms", "-")
        record.container_id = getattr(
            record,
            "container_id",
            os.environ.get("HOSTNAME", "unknown"),
        )
        record.worker_pid = getattr(record, "worker_pid", os.getpid())
        record.worker_name = getattr(
            record,
            "worker_name",
            os.environ.get("GUNICORN_WORKER_NAME", f"worker-{os.getpid()}"),
        )
        record.worker_thread_name = getattr(
            record,
            "worker_thread_name",
            threading.current_thread().name,
        )
        return True


def configure_observability(app):

    #
    # Tracing
    #
    trace_provider = TracerProvider(resource=resource)
    trace_provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{OTEL_COLLECTOR}/v1/traces")
        )
    )
    trace.set_tracer_provider(trace_provider)

    #
    # Metrics
    #
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{OTEL_COLLECTOR}/v1/metrics")
    )
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader],
    )
    metrics.set_meter_provider(meter_provider)

    #
    # Logs — send directly to OTel collector instead of relying on stdout scraping
    #
    logger_provider = LoggerProvider(resource=resource)
    set_logger_provider(logger_provider)

    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(OTLPLogExporter(endpoint=f"{OTEL_COLLECTOR}/v1/logs"))
    )

    # Inject OTEL trace context into stdlib log records
    LoggingInstrumentor().instrument(set_logging_format=False)

    root_logger = logging.getLogger()
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))
    root_logger.handlers.clear()

    # OTLP handler — ships structured log records straight to the collector
    otlp_handler = LoggingHandler(
        level=logging.INFO,
        logger_provider=logger_provider,
    )
    otlp_handler.addFilter(OtelContextFilter())
    root_logger.addHandler(otlp_handler)

    # Console handler — still useful for `kubectl logs`, now with full context
    console_handler = logging.StreamHandler()
    console_handler.addFilter(OtelContextFilter())
    console_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s "
            "%(levelname)s "
            "%(name)s "
            "%(message)s "
            "service_name=%(service_name)s "
            "request_id=%(request_id)s "
            "trace_id=%(otelTraceID)s "
            "span_id=%(otelSpanID)s "
            "container_id=%(container_id)s "
            "worker_pid=%(worker_pid)s "
            "worker_thread_name=%(worker_thread_name)s "
            "worker_name=%(worker_name)s "
            "query_id=%(query_id)s "
            "client_wait_ms=%(client_wait_ms)s "
        )
    )
    root_logger.addHandler(console_handler)

    #
    # Flask
    #
    FlaskInstrumentor().instrument_app(app)


tracer = trace.get_tracer(SERVICE_NAME)
meter = metrics.get_meter(SERVICE_NAME)
logger = logging.getLogger(SERVICE_NAME)
