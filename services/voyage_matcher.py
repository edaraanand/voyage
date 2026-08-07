import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

import clickhouse_connect
from observability import logger, request_id_ctx, tracer
from opentelemetry import context
from opentelemetry.trace import Status, StatusCode
from queries.voyage_queries import QUERIES
import os
import urllib3

def runtime_context():
    return {
        "container_id": os.environ.get("HOSTNAME", "unknown"),  # NEW — unique per Docker replica
        "worker_pid": os.getpid()
    }

class VoyageMatcher:
    def __init__(self, pool_size=12):
        self.clickhouse_config = {
            "host": "bdx31tl6ut.us-central1.gcp.clickhouse.cloud",
            "username": "username",
            "password": "password",
            "database": "default",
            "secure": True,
        }

        self.pool_size = pool_size

        # Shared pool manager with maxsize >= pool_size, so all `pool_size`
        # clients in this worker can hold a live connection simultaneously
        # without urllib3 discarding any on release.
        pool_mgr = urllib3.PoolManager(maxsize=max(pool_size, len(QUERIES)))

        self._pool = queue.Queue()
        for _ in range(pool_size):
            self._pool.put(
                clickhouse_connect.get_client(
                    **self.clickhouse_config,
                    pool_mgr=pool_mgr,
                )
            )
        # NEW — the missing piece
        self._executor = ThreadPoolExecutor(max_workers=len(QUERIES))

    def get_client(self):
        client = clickhouse_connect.get_client(**self.clickhouse_config)

        logger.info(
            "clickhouse_client_created request_id=%s",
            request_id_ctx.get(),
            extra={
                "client_id": id(client),
            },
        )

        return client

    @staticmethod
    def substitute_query(query, params):
        result = query

        for key, value in params.items():
            placeholder = f"%({key})s"

            if value is None:
                replacement = "NULL"
            elif isinstance(value, str):
                # Escape single quotes using SQL standard escaping.
                replacement = "'" + value.replace("'", "''") + "'"
            elif isinstance(value, bool):
                replacement = "1" if value else "0"
            else:
                replacement = str(value)

            result = result.replace(placeholder, replacement)

        return result

    def execute_query(
        self,
        query_id,
        query,
        params,
    ):
        wait_start = time.perf_counter()
        available_clients_before = self._pool.qsize()
        client = self._pool.get()
        client_id = id(client)
        wait_ms = (time.perf_counter() - wait_start) * 1000

        try:
            with tracer.start_as_current_span(f"query-{query_id}") as span:
                try:
                    # substituted_query = query % params
                    debug_query = self.substitute_query(query, params)

                    start_time = time.perf_counter()

                    span.set_attribute(
                        "voyage.query.id",
                        query_id,
                    )

                    span.set_attribute(
                        "voyage.query",
                        debug_query,
                    )

                    logger.info(
                        "query_started: query_id=%s request_id=%s client_wait_ms=%.2f container_id=%s worker_pid=%s",
                        query_id,
                        request_id_ctx.get(),
                        wait_ms,
                        os.environ.get("HOSTNAME", "unknown"),
                        os.getpid(),
                        extra={
                            "query_id": query_id,
                            "query": debug_query,
                            "client_id": client_id,
                            "available_clients_before": available_clients_before,
                        },
                    )

                    result = client.query(
                        query,
                        parameters=params,
                    )

                    elapsed_ms = (time.perf_counter() - start_time) * 1000

                    rows = len(result.result_rows)

                    matched = rows > 0

                    span.set_attribute(
                        "voyage.query.duration_ms",
                        elapsed_ms,
                    )

                    span.set_attribute(
                        "voyage.query.rows",
                        rows,
                    )

                    span.set_attribute(
                        "voyage.query.matched",
                        matched,
                    )

                    logger.info(
                        "query_completed query_id=%s request_id=%s query_completed=%s container_id=%s worker_pid=%s",
                        query_id,
                        request_id_ctx.get(),
                        round(elapsed_ms,2),
                        os.environ.get("HOSTNAME", "unknown"),
                        os.getpid(),
                        extra={
                            "query_id": query_id,
                            "query": debug_query,
                            "duration_ms": round(
                                elapsed_ms,
                                2,
                            ),
                            "rows": rows,
                            "matched": matched,
                            "status": 200,
                        }
                    )


                    return {
                        "query_id": query_id,
                        "rows": result.result_rows,
                        "columns": result.column_names,
                        "duration_ms": round(elapsed_ms, 2)
                    }

                except Exception as ex:
                    span.record_exception(ex)

                    span.set_status(
                        Status(
                            StatusCode.ERROR,
                            str(ex),
                        )
                    )

                    logger.exception(
                        "query_failed",
                        extra={
                            "query_id": query_id,
                            "status": 500,
                        },
                    )

                    raise
        finally:
            self._pool.put(client) # return, never client.close()

    def execute_query_with_context(
        self,
        parent_context,
        request_id,
        query_id,
        query,
        params,
    ):

        token = context.attach(parent_context)

        request_token = request_id_ctx.set(request_id)

        try:
            return self.execute_query(
                query_id,
                query,
                params,
            )

        finally:
            request_id_ctx.reset(request_token)

            context.detach(token)

    def match(
        self,
        request,
    ):

        request_start = time.perf_counter()

        with tracer.start_as_current_span("voyage.match") as span:
            params = {
                "port_city": request.get("port_city"),
                "email_contact": request.get("email_contact"),
                "given_name": request.get("given_name"),
                "surname": request.get("surname"),
                "maritime_account_id": request.get("maritime_account_id"),
                "contact_number": request.get("contact_number"),
                "zip_code": request.get("zip_code"),
                "address_line_1": request.get("address_line_1"),
                "address_line_2": request.get("address_line_2"),
                "date_of_birth": request.get("date_of_birth"),
                "membership_start_date_1": request.get("membership_start_date_1"),
            }

            span.set_attribute(
                "voyage.request.has_account_id",
                params["maritime_account_id"] is not None,
            )

            logger.info(
                "match_started request_id=%s container_id=%s worker_pid=%s",
                request_id_ctx.get(),
                os.environ.get("HOSTNAME", "unknown"),
                os.getpid(),
                extra={
                    "endpoint": "/match",
                },
            )

            matches = []

            parent_context = context.get_current()

            request_id = request_id_ctx.get()

            db_start = time.perf_counter()

            futures = {
                self._executor.submit(
                    self.execute_query_with_context,
                    parent_context,
                    request_id,
                    query_id,
                    query,
                    params,
                ): query_id
                for query_id, query in QUERIES.items()
            }

            for future in as_completed(futures):
                result = future.result()

                if result["rows"]:
                    matches.append(result)

            db_wall_time_ms = (time.perf_counter() - db_start) * 1000

            total_time_ms = (time.perf_counter() - request_start) * 1000

            if not matches:
                span.set_attribute(
                    "voyage.match.success",
                    False,
                )

                logger.info(
                    "match_not_found request_id=%s",
                    request_id_ctx.get(),
                    extra={
                        "endpoint": "/match",
                        "duration_ms": round(
                            total_time_ms,
                            2,
                        ),
                        "db_time_ms": round(db_wall_time_ms, 2),
                        "status": 200,
                        "matched": False,
                        **runtime_context()
                    },
                )

                return {
                    "matched": False,
                    "request_id": request_id_ctx.get(),
                    "db_time_ms": round(db_wall_time_ms, 2),
                }

            best_match = min(
                matches,
                key=lambda x: x["query_id"],
            )

            span.set_attribute(
                "voyage.match.query_id",
                best_match["query_id"],
            )

            span.set_attribute(
                "voyage.match.success",
                True,
            )

            logger.info(
                "match_found request_id=%s",
                request_id_ctx.get(),
                extra={
                    "endpoint": "/match",
                    "duration_ms": round(
                        total_time_ms,
                        2,
                    ),
                    "db_time_ms": round(db_wall_time_ms, 2),
                    "status": 200,
                    "matched": True,
                    "query_id": best_match["query_id"],
                    **runtime_context()
                },
            )

            return {
                "matched": True,
                "request_id": request_id_ctx.get(),
                "query": best_match["query_id"],
                "db_time_ms": round(db_wall_time_ms, 2)
            }
