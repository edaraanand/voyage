import time
import uuid

from flask import Flask, g, jsonify, request
from observability import (
    configure_observability,
    logger,
    request_id_ctx,
)
from services.voyage_matcher import VoyageMatcher

app = Flask(__name__)

configure_observability(app)

matcher = VoyageMatcher()


@app.before_request
def add_request_context():

    request_id = request.headers.get(
        "X-Request-ID",
        str(uuid.uuid4()),
    )

    g.request_id_token = request_id_ctx.set(request_id)


@app.after_request
def clear_request_context(response):

    token = getattr(
        g,
        "request_id_token",
        None,
    )

    if token:
        request_id_ctx.reset(token)

    return response


@app.get("/health")
def health():

    logger.info(
        "health_check",
        extra={
            "endpoint": "/health",
            "status": 200,
        },
    )

    return jsonify(
        {
            "status": "ok",
        }
    )


@app.post("/voyage/match")
def voyage_match():

    start = time.perf_counter()

    try:
        print(request.json)

        result = matcher.match(request.json)

        total_ms = (time.perf_counter() - start) * 1000
        result["response_time_ms"] = round(total_ms, 2)
        db_time_ms = result["db_time_ms"]

        logger.info(
            "request_completed successful request_id=%s response_time=%d",
            request_id_ctx.get(),
            round(total_ms,2),
            extra={
                "endpoint": "/voyage/match",
                "duration_ms": round(
                    total_ms,
                    2,
                ),
                "db_time_ms": round(db_time_ms, 2),
                "status": 200,
                "matched": result.get(
                    "matched",
                    False,
                ),
            },
        )

        return jsonify(result), 200

    except Exception:
        total_ms = (time.perf_counter() - start) * 1000

        logger.exception(
            "request_completed failed request_id=%s response_time=%d",
            request_id_ctx.get(),
            round(total_ms,2),
            extra={
                "endpoint": "/voyage/match",
                "duration_ms": round(
                    total_ms,
                    2,
                ),
                "status": 500,
            },
        )

        return jsonify(
            {
                "error": "internal server error",
                "request_id": request_id_ctx.get(),
            }
        ), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=True,
    )

"""
gunicorn \
  --bind 0.0.0.0:5003 \
  --workers 2 \
  --threads 4 \
  app:app

Container
│
└── Gunicorn
    │
    ├── Master Process
    │
    ├── Worker Process PID 8
    │   │
    │   ├── Request Thread Pool (4 threads)
    │   │   │
    │   │   ├── Request Thread 1
    │   │   │   │
    │   │   │   └── Application code
    │   │   │       │
    │   │   │       └── matcher.match()
    │   │   │           │
    │   │   │           └── ThreadPoolExecutor (12)
    │   │   │               ├── Query Thread 1  - ThreadPoolExecutor-3_0  <-- query
    │   │   │               ├── Query Thread .  - ThreadPoolExecutor-3_1  <-- query
    │   │   │               └── Query Thread 12 - ThreadPoolExecutor-3_9  <-- query
    │   │   │
    │   │   ├── Request Thread 2
    │   │   ├── Request Thread 3
    │   │   └── Request Thread 4
    │   │
    │   └── Other process resources
    │
    └── Worker Process PID 9
        │
        ├── Request Thread Pool (4 threads)
        │   │
        │   ├── Request Thread 1
        │   │   │
        │   │   ├── Request Thread 1
        │   │   │   │
        │   │   │   └── Application code
        │   │   │       │
        │   │   │       └── matcher.match()
        │   │   │           │
        │   │   │           └── ThreadPoolExecutor (12)
        │   │   │               ├── Query Thread 1  - ThreadPoolExecutor-3_0  <-- query
        │   │   │               ├── Query Thread .  - ThreadPoolExecutor-3_1  <-- query
        │   │   │               └── Query Thread 12 - ThreadPoolExecutor-3_9  <-- query
        │   │   │
        │   ├── Request Thread 2
        │   ├── Request Thread 3
        │   └── Request Thread 4
        │
        └── Other process resources


Gunicorn worker process (PID 8)
│
├── Gunicorn request thread
│       |
│       | calls matcher.match()
│       |
│       └── ThreadPoolExecutor
│               |
│               ├── ThreadPoolExecutor-3_0  <-- query
│               ├── ThreadPoolExecutor-3_1  <-- query
│               ├── ThreadPoolExecutor-3_2  <-- query
│               └── ThreadPoolExecutor-3_9  <-- query


"""
