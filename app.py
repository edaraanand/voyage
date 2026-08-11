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


# ---------------------------------------------------------
# REQUEST CONTEXT
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# BAD REQUEST
# ---------------------------------------------------------

@app.errorhandler(400)
def handle_bad_request(error):

    request_id = request_id_ctx.get()

    logger.warning(
        "request_completed",
        extra={
            "event": "request_completed",
            "request_id": request_id,
            "endpoint": request.path,
            "method": request.method,
            "status": 400,
            "status_class": "4xx",
            "success": False,
            "matched": False,
            "timed_out": False,
        },
    )

    return jsonify(
        {
            "success": False,
            "matched": False,
            "timed_out": False,
            "error": "bad request",
            "request_id": request_id,
        }
    ), 400


# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# VOYAGE MATCH
# ---------------------------------------------------------

@app.post("/voyage/match")
def voyage_match():

    start = time.perf_counter()

    request_id = request_id_ctx.get()

    try:

        # -------------------------------------------------
        # Validate request body
        # -------------------------------------------------

        payload = request.get_json(silent=True)

        if payload is None:

            total_ms = (
                time.perf_counter() - start
            ) * 1000

            logger.warning(
                "request_completed request_id=%s",
                request_id,
                extra={
                    "event": "request_completed",
                    "request_id": request_id,
                    "endpoint": "/voyage/match",
                    "method": "POST",
                    "status": 400,
                    "status_class": "4xx",
                    "duration_ms": round(total_ms, 2),
                    "success": False,
                    "matched": False,
                    "timed_out": False,
                },
            )

            return jsonify(
                {
                    "success": False,
                    "matched": False,
                    "timed_out": False,
                    "error": "request body must be valid JSON",
                    "request_id": request_id,
                }
            ), 400

        # -------------------------------------------------
        # Execute matching
        # -------------------------------------------------

        result = matcher.match(payload)

        total_ms = (
            time.perf_counter() - start
        ) * 1000

        result["response_time_ms"] = round(
            total_ms,
            2,
        )

        db_time_ms = result.get(
            "db_time_ms",
            0,
        )

        success = result.get(
            "success",
            False,
        )

        matched = result.get(
            "matched",
            False,
        )

        timed_out = result.get(
            "timed_out",
            False,
        )

        # -------------------------------------------------
        # Determine HTTP status
        # -------------------------------------------------

        if timed_out:

            http_status = 504
            status_class = "5xx"

        elif not success:

            http_status = 500
            status_class = "5xx"

        else:

            http_status = 200
            status_class = "2xx"

        # -------------------------------------------------
        # Request completed log
        # -------------------------------------------------

        logger.info(
            "request_completed request_id=%s",
            request_id,
            extra={
                "event": "request_completed",
                "request_id": request_id,
                "endpoint": "/voyage/match",
                "method": "POST",
                "status": http_status,
                "status_class": status_class,
                "duration_ms": round(
                    total_ms,
                    2,
                ),
                "db_time_ms": round(
                    db_time_ms,
                    2,
                ),
                "success": success,
                "matched": matched,
                "timed_out": timed_out,
            },
        )

        return jsonify(result), http_status

    except Exception:

        total_ms = (
            time.perf_counter() - start
        ) * 1000

        logger.exception(
            "request_completed request_id=%s",
            request_id,
            extra={
                "event": "request_completed",
                "request_id": request_id,
                "endpoint": "/voyage/match",
                "method": "POST",
                "status": 500,
                "status_class": "5xx",
                "duration_ms": round(
                    total_ms,
                    2,
                ),
                "success": False,
                "matched": False,
                "timed_out": False,
            },
        )

        return jsonify(
            {
                "success": False,
                "matched": False,
                "timed_out": False,
                "error": "internal server error",
                "request_id": request_id,
            }
        ), 500


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=5003,
        debug=True,
    )
