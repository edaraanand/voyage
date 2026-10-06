QUERY1 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM customer_voyage_profile_v3
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND date_of_birth = %(date_of_birth)s
LIMIT 1
"""


QUERY2 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM customer_voyage_profile_v3
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND lower(email_contact) = lower(%(email_contact)s)
  AND date_of_birth = %(date_of_birth)s
  AND lower(surname) != lower(%(surname)s)
LIMIT 1
"""


QUERY3 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM customer_voyage_profile_v3
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND contact_number = toString(%(contact_number)s)
  AND date_of_birth = %(date_of_birth)s
  AND lower(surname) != lower(%(surname)s)
LIMIT 1
"""


QUERY4 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM customer_voyage_profile_v3
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND lower(address_line_1) LIKE lower(%(address_line_1)s)
  AND lower(address_line_2) LIKE lower(%(address_line_2)s)
  AND lower(port_city) = lower(%(port_city)s)
  AND date_of_birth = %(date_of_birth)s
  AND lower(surname) != lower(%(surname)s)
LIMIT 1
"""


QUERY5 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM customer_voyage_profile_v3
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND lower(email_contact) = lower(%(email_contact)s)
  AND date_of_birth = %(date_of_birth)s
ORDER BY most_recent_sailing_date_1 DESC
LIMIT 1
"""


QUERY6 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM default.customer_voyage_profile_v3
WHERE contact_number = toString(%(contact_number)s)
ORDER BY most_recent_sailing_date_1 DESC
LIMIT 1
SETTINGS
    max_execution_time = 10,
    max_threads = 4,
    optimize_use_projections = 1,
    optimize_use_projection_filtering = 1,
    use_query_cache = 0,
    use_query_condition_cache = 0;
"""


QUERY7 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM customer_voyage_profile_v3
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND lower(email_contact) = lower(%(email_contact)s)
  AND contact_number = toString(%(contact_number)s)
  AND date_of_birth = %(date_of_birth)s
LIMIT 1
"""


# QUERY8 = """
# SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
# FROM customer_voyage_profile_v3
# WHERE lower(address_line_1) LIKE lower(%(address_line_1)s)
#   AND lower(address_line_2) LIKE lower(%(address_line_2)s)
#   AND lower(port_city) = lower(%(port_city)s)
#   AND substr(toString(zip_code), 1, 5) = substr(toString(%(zip_code)s), 1, 5)
# ORDER BY most_recent_sailing_date_1 DESC
# LIMIT 1
# """

QUERY8 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM default.customer_voyage_profile_v3
WHERE lower(address_line_1) = lower(%(address_line_1)s)
  AND lower(address_line_2) = lower(%(address_line_2)s)
  AND lower(port_city) = lower(%(port_city)s)
  AND substring(zip_code, 1, 5) = substring(toString(%(zip_code)s), 1, 5)
ORDER BY most_recent_sailing_date_1 DESC
LIMIT 1
SETTINGS
    max_execution_time = 10,
    max_threads = 4,
    optimize_use_projections = 1,
    optimize_use_projection_filtering = 1,
    use_query_cache = 0,
    use_query_condition_cache = 0;
"""

# QUERY9 = """
# SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
# FROM customer_voyage_profile_v3
# WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
# LIMIT 1
# """

QUERY9 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM default.customer_voyage_profile_v3
WHERE
    (date_of_birth, lower(surname), lower(given_name), maritime_account_id)
    IN
    (
        SELECT
            date_of_birth,
            lower(surname),
            lower(given_name),
            maritime_account_id
        FROM default.customer_voyage_profile_v3
        WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
        LIMIT 1
    )
LIMIT 1
SETTINGS
    max_execution_time = 10,
    timeout_overflow_mode = 'throw',
    max_threads = 4,
    optimize_use_projections = 1,
    use_query_cache = 0,
    use_query_condition_cache = 0,
    use_skip_indexes_on_data_read = 0,
    use_skip_indexes = 0;
"""

QUERY10 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM customer_voyage_profile_v3
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND lower(email_contact) = lower(%(email_contact)s)
  AND date_of_birth = %(date_of_birth)s
ORDER BY membership_start_date_1 ASC
LIMIT 1
"""


QUERY11 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM default.customer_voyage_profile_v3
WHERE contact_number = toString(%(contact_number)s)
ORDER BY membership_start_date_1 ASC
LIMIT 1
SETTINGS
    max_execution_time = 10,
    max_threads = 4,
    optimize_use_projections = 1,
    optimize_use_projection_filtering = 1,
    use_query_cache = 0,
    use_query_condition_cache = 0;
"""


# QUERY12 = """
# SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
# FROM customer_voyage_profile_v3
# WHERE lower(address_line_1) LIKE lower(%(address_line_1)s)
#   AND lower(address_line_2) LIKE lower(%(address_line_2)s)
#   AND lower(port_city) = lower(%(port_city)s)
#   AND substr(toString(zip_code), 1, 5) = substr(toString(%(zip_code)s), 1, 5)
# ORDER BY membership_start_date_1 ASC
# LIMIT 1
# """

QUERY12 = """
SELECT * EXCEPT(str_metrics, int_metrics, date_metrics)
FROM default.customer_voyage_profile_v3
WHERE lower(address_line_1) = lower(%(address_line_1)s)
  AND lower(address_line_2) = lower(%(address_line_2)s)
  AND lower(port_city) = lower(%(port_city)s)
  AND substring(zip_code, 1, 5) = substr(toString(%(zip_code)s), 1, 5)
ORDER BY membership_start_date_1 ASC
LIMIT 1
SETTINGS
    max_execution_time = 10,
    timeout_overflow_mode = 'throw',
    max_threads = 1,
    optimize_use_projections = 1,
    optimize_use_projection_filtering = 1,
    use_query_cache = 0,
    use_query_condition_cache = 0,
    use_skip_indexes_on_data_read = 0,
    use_skip_indexes = 0;
"""

QUERIES = {
    1: QUERY1,
    2: QUERY2,
    3: QUERY3,
    4: QUERY4,
    5: QUERY5,
    6: QUERY6,
    7: QUERY7,
    8: QUERY8,
    9: QUERY9,
    10: QUERY10,
    11: QUERY11,
    12: QUERY12,
}
