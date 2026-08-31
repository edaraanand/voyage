import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue

import clickhouse_connect
from observability import logger, request_id_ctx, tracer
from opentelemetry import context
from opentelemetry.trace import Status, StatusCode
from queries.voyage_queries import QUERIES
import os
import urllib3

# ---------------------------------------------------------------------------
# Config -- pulled from env so this file and the Dockerfile can't drift out
# of sync with each other. All of these were previously hardcoded constants.
# ---------------------------------------------------------------------------

# How long ClickHouse itself is allowed to run a single query before it
# kills it server-side and returns an error we can handle cleanly. This is
# now actually enforced (see execute_query below) -- previously this
# constant existed and was used for logging/classification, but the
# `max_execution_time` setting that enforces it was commented out, so
# slow queries could run indefinitely, holding a pooled connection and a
# thread hostage until gunicorn's own --timeout SIGKILLed the whole worker.
QUERY_TIMEOUT_SECONDS = int(os.environ.get("QUERY_TIMEOUT_SECONDS", 1))

# How many requests THIS PROCESS will allow to be actively running their
# fan-out of 12 queries at the same time. Anything beyond this queues on a
# semaphore instead of being admitted straight into ClickHouse.
#
# This is the main lever for controlling how much of ClickHouse's shared
# max_concurrent_queries_for_all_users budget (1000, in your case) your
# fleet can consume. Rough sizing:
#
#   fleet concurrent queries <= containers * GUNICORN_WORKERS
#                               * MAX_CONCURRENT_REQUESTS * N_QUERIES
#
# Solve that for whatever headroom you want to leave other workloads on
# the same ClickHouse Cloud instance before raising this.
MAX_CONCURRENT_REQUESTS = int(os.environ.get("MAX_CONCURRENT_REQUESTS", 2))

N_QUERIES = len(QUERIES)

def runtime_context():
    return {
        # NEW — unique per Docker replica
        "container_id": os.environ.get("HOSTNAME", "unknown"),
        "worker_pid": os.getpid()
    }


class VoyageMatcher:
    def __init__(self):
        self.clickhouse_config = {
            "host": "bdx31tl6ut.us-central1.gcp.clickhouse.cloud",
            "username": os.environ["CLICKHOUSE_USERNAME"],
            "password": os.environ["CLICKHOUSE_PASSWORD"],
            "database": "default",
            "secure": True,
        }

        # Pool size = MAX_CONCURRENT_REQUESTS * N_QUERIES, i.e. exactly
        # enough clients for every admitted request to have one client per
        # query in flight, with no spare headroom. That's intentional: the
        # semaphore in match() is what enforces MAX_CONCURRENT_REQUESTS, so
        # the pool should never actually be asked for more clients than it
        # has. If you ever see execute_query's wait_ms climb, that means
        # something is bypassing the semaphore, not that the pool is
        # undersized -- don't "fix" that by just growing the pool number,
        # since every unit here is also a persistent connection to
        # ClickHouse Cloud, multiplied across every worker in every
        # container in the fleet.
        self._pool_size = MAX_CONCURRENT_REQUESTS * N_QUERIES

        pool_mgr = urllib3.PoolManager(maxsize=self._pool_size)

        self._pool = queue.Queue()

        for _ in range(self._pool_size):
            self._pool.put(
                clickhouse_connect.get_client(
                    **self.clickhouse_config,
                    pool_mgr=pool_mgr,
                )
            )

        self._executor = ThreadPoolExecutor(max_workers=self._pool_size)

        # Caps how many *requests* (not queries) this process will run
        # concurrently. Without this, a burst of incoming requests would
        # all submit their 12 queries at once, immediately draining the
        # client pool and forcing everyone after them to block inside
        # execute_query()'s self._pool.get() -- which shows up as
        # increased db_time_ms even though ClickHouse itself may be fine.
        # This semaphore turns that same wait into an explicit, visible
        # queue point instead, and gives you a place to measure it.
        self._admission = threading.Semaphore(MAX_CONCURRENT_REQUESTS)

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
        request_id,
    ):
        wait_start = time.perf_counter()

        available_clients_before = self._pool.qsize()

        client = self._pool.get()

        client_id = id(client)

        ch_query_id = f"{request_id}-{query_id}"

        wait_ms = (time.perf_counter() - wait_start) * 1000

        try:
            with tracer.start_as_current_span(
                f"query-{query_id}"
            ) as span:

                debug_query = self.substitute_query(
                    query,
                    params,
                )

                start_time = time.perf_counter()

                span.set_attribute("voyage.query.id", query_id)
                span.set_attribute("voyage.query", debug_query)
                span.set_attribute("voyage.ch_query_id", ch_query_id)
                span.set_attribute("voyage.query.client_wait_ms", wait_ms)

                logger.info(
                    "query_started: query_id=%s request_id=%s client_wait_ms=%.2f",
                    query_id,
                    request_id_ctx.get(),
                    wait_ms,
                    extra={
                        "query_id": query_id,
                        "query": debug_query,
                        "ch_query_id": ch_query_id,
                        "client_id": client_id,
                        "available_clients_before": available_clients_before,
                        "client_wait_ms": round(wait_ms, 2),
                    },
                )

                try:
                    result = client.query(
                        query,
                        parameters=params,
                        settings={
                            "query_id": ch_query_id,
                            "log_comment":
                                f"voyage|request={request_id}|query={query_id}",
                            # This is the fix: previously commented out, so
                            # ClickHouse would let a query run indefinitely.
                            # Now ClickHouse itself enforces the cutoff and
                            # returns a clean, catchable error instead of
                            # the query (and the connection + thread holding
                            # it) hanging until gunicorn's own timeout
                            # SIGKILLs the whole worker process.
                            "max_execution_time": QUERY_TIMEOUT_SECONDS,
                        },
                    )

                except Exception as ex:

                    elapsed_ms = (
                        time.perf_counter() - start_time
                    ) * 1000

                    error_message = str(ex)

                    is_timeout = (
                        "TIMEOUT" in error_message.upper()
                        or "TIMEOUT_EXCEEDED" in error_message.upper()
                        or "MAX_EXECUTION_TIME" in error_message.upper()
                    )

                    if is_timeout:

                        span.set_attribute("voyage.query.timed_out", True)
                        span.set_attribute(
                            "voyage.query.duration_ms", elapsed_ms
                        )

                        logger.warning(
                            "query_timeout "
                            "query_id=%s request_id=%s",
                            query_id,
                            request_id,
                            extra={
                                "query_id": query_id,
                                "ch_query_id": ch_query_id,
                                "duration_ms": round(elapsed_ms, 2),
                                "timeout_seconds": QUERY_TIMEOUT_SECONDS,
                                "error": error_message,
                            },
                        )

                        return {
                            "query_id": query_id,
                            "rows": [],
                            "columns": [],
                            "duration_ms": round(elapsed_ms, 2),
                            "success": False,
                            "timed_out": True,
                            "error": error_message,
                        }

                    # -----------------------------------------
                    # NON-TIMEOUT QUERY ERROR
                    # -----------------------------------------

                    span.record_exception(ex)
                    span.set_status(Status(StatusCode.ERROR, str(ex)))

                    logger.exception(
                        "query_failed",
                        extra={
                            "query_id": query_id,
                            "ch_query_id": ch_query_id,
                            "duration_ms": round(elapsed_ms, 2),
                        },
                    )

                    return {
                        "query_id": query_id,
                        "rows": [],
                        "columns": [],
                        "duration_ms": round(elapsed_ms, 2),
                        "success": False,
                        "timed_out": False,
                        "error": error_message,
                    }

                # ---------------------------------------------
                # QUERY SUCCEEDED
                # ---------------------------------------------

                elapsed_ms = (time.perf_counter() - start_time) * 1000

                rows = len(result.result_rows)

                matched = rows > 0

                span.set_attribute("voyage.query.duration_ms", elapsed_ms)
                span.set_attribute("voyage.query.rows", rows)
                span.set_attribute("voyage.query.matched", matched)
                span.set_attribute("voyage.query.timed_out", False)

                logger.info(
                    "query_completed "
                    "query_id=%s request_id=%s "
                    "duration_ms=%.2f",
                    query_id,
                    request_id_ctx.get(),
                    elapsed_ms,
                    extra={
                        "query_id": query_id,
                        "query": debug_query,
                        "ch_query_id": ch_query_id,
                        "duration_ms": round(elapsed_ms, 2),
                        "rows": rows,
                        "matched": matched,
                        "status": 200,
                    },
                )

                return {
                    "query_id": query_id,
                    "rows": result.result_rows,
                    "columns": result.column_names,
                    "duration_ms": round(elapsed_ms, 2),
                    "success": True,
                    "timed_out": False,
                }

        finally:
            self._pool.put(client)

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
                request_id
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
                extra={"endpoint": "/match"},
            )

            # Admission control: block here (not inside execute_query) so
            # the queueing is explicit and measurable, rather than showing
            # up silently as extra db_time_ms once queries start competing
            # for pool clients they were never guaranteed to get.
            admission_wait_start = time.perf_counter()
            self._admission.acquire()
            admission_wait_ms = (
                time.perf_counter() - admission_wait_start
            ) * 1000

            span.set_attribute(
                "voyage.request.admission_wait_ms", admission_wait_ms
            )

            if admission_wait_ms > 0:
                logger.info(
                    "match_admission_wait request_id=%s wait_ms=%.2f",
                    request_id_ctx.get(),
                    admission_wait_ms,
                    extra={
                        "endpoint": "/match",
                        "admission_wait_ms": round(admission_wait_ms, 2),
                    },
                )

            try:
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

                matches = []
                timed_out_queries = []
                failed_queries = []

                # Wait for ALL queries to complete.
                #
                # There is intentionally NO application-level timeout here.
                #
                # Each individual ClickHouse query now has its own
                # server-enforced QUERY_TIMEOUT_SECONDS timeout (see
                # max_execution_time above), so this loop is guaranteed to
                # finish within roughly QUERY_TIMEOUT_SECONDS of the last
                # query starting, rather than being able to hang
                # indefinitely as it could before.
                for future in as_completed(futures):
                    query_id = futures[future]

                    try:
                        result = future.result()

                        if result["timed_out"]:
                            timed_out_queries.append(query_id)

                        elif not result["success"]:
                            failed_queries.append({
                                "query_id": query_id,
                                "error": result.get("error"),
                            })

                        elif result["rows"]:
                            matches.append(result)

                    except Exception as ex:
                        failed_queries.append({
                            "query_id": query_id,
                            "error": str(ex),
                        })

                        logger.exception(
                            "query_future_failed",
                            extra={
                                "query_id": query_id,
                                "request_id": request_id,
                                **runtime_context(),
                            },
                        )

                db_wall_time_ms = (time.perf_counter() - db_start) * 1000

                total_time_ms = (
                    time.perf_counter() - request_start
                ) * 1000

                # ---------------------------------------------------------
                # ANY QUERY TIMEOUT
                #
                # ClickHouse itself timed out one or more queries.
                # This is the only timeout being handled here.
                # ---------------------------------------------------------
                if timed_out_queries:

                    return {
                        "success": False,
                        "matched": False,
                        "timed_out": True,
                        "timed_out_queries": timed_out_queries,
                        "request_timeout_queries": [],
                        "request_id": request_id,
                        "db_time_ms": round(db_wall_time_ms, 2),
                        "admission_wait_ms": round(admission_wait_ms, 2),
                    }

                # ---------------------------------------------------------
                # ANY NON-TIMEOUT QUERY ERROR
                #
                # A query failed, but it did not time out.
                # ---------------------------------------------------------

                if failed_queries:

                    return {
                        "success": False,
                        "matched": False,
                        "timed_out": False,
                        "request_timeout": False,
                        "failed_queries": failed_queries,
                        "request_id": request_id,
                        "db_time_ms": round(db_wall_time_ms, 2),
                        "admission_wait_ms": round(admission_wait_ms, 2),
                    }

                # ---------------------------------------------------------
                # ALL QUERIES SUCCEEDED, BUT NOTHING MATCHED
                # ---------------------------------------------------------

                if not matches:

                    span.set_attribute("voyage.match.success", False)

                    logger.info(
                        "match_not_found request_id=%s",
                        request_id_ctx.get(),
                        extra={
                            "endpoint": "/match",
                            "duration_ms": round(total_time_ms, 2),
                            "db_time_ms": round(db_wall_time_ms, 2),
                            "admission_wait_ms": round(admission_wait_ms, 2),
                            "status": 200,
                            "matched": False,
                            "success": True,
                            "timed_out": False,
                            "request_timeout": False,
                            **runtime_context(),
                        },
                    )

                    return {
                        "success": True,
                        "matched": False,
                        "timed_out": False,
                        "request_timeout": False,
                        "timed_out_queries": [],
                        "request_id": request_id,
                        "db_time_ms": round(db_wall_time_ms, 2),
                        "admission_wait_ms": round(admission_wait_ms, 2),
                    }

                # ---------------------------------------------------------
                # MATCH FOUND
                # ---------------------------------------------------------

                best_match = min(matches, key=lambda x: x["query_id"])

                span.set_attribute(
                    "voyage.match.query_id", best_match["query_id"]
                )
                span.set_attribute("voyage.match.success", True)

                logger.info(
                    "match_found request_id=%s",
                    request_id_ctx.get(),
                    extra={
                        "endpoint": "/match",
                        "duration_ms": round(total_time_ms, 2),
                        "db_time_ms": round(db_wall_time_ms, 2),
                        "admission_wait_ms": round(admission_wait_ms, 2),
                        "status": 200,
                        "matched": True,
                        "success": True,
                        "timed_out": False,
                        "request_timeout": False,
                        "query_id": best_match["query_id"],
                        **runtime_context(),
                    },
                )

                return {
                    "success": True,
                    "matched": True,
                    "timed_out": False,
                    "request_timeout": False,
                    "timed_out_queries": [],
                    "request_id": request_id,
                    "query": best_match["query_id"],
                    "db_time_ms": round(db_wall_time_ms, 2),
                    "admission_wait_ms": round(admission_wait_ms, 2),
                }

            finally:
                self._admission.release()
