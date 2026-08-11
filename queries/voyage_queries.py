# queries/poc_queries.py

QUERY1 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 1 AS match_criteria
FROM customer_voyage_profile
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND date_of_birth = %(date_of_birth)s
LIMIT 1
"""


QUERY2 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 2 AS match_criteria
FROM customer_voyage_profile
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND lower(email_contact) = lower(%(email_contact)s)
  AND date_of_birth = %(date_of_birth)s
LIMIT 1
"""


QUERY3 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1,  3 AS match_criteria
FROM customer_voyage_profile
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND date_of_birth = %(date_of_birth)s
  AND contact_number = toString(%(contact_number)s)
LIMIT 1
"""


QUERY4 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 4 AS match_criteria
FROM customer_voyage_profile
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND date_of_birth = %(date_of_birth)s
  AND lower(port_city) = lower(%(port_city)s)
  AND substr(lower(address_line_1), 1, least(length(%(address_line_1)s), 9))
      = substr(lower(%(address_line_1)s), 1, least(length(%(address_line_1)s), 9))
  AND substr(lower(address_line_2), 1, least(length(%(address_line_2)s), 9))
      = substr(lower(%(address_line_2)s), 1, least(length(%(address_line_2)s), 9))
LIMIT 1
"""


QUERY5 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 5 AS match_criteria
FROM customer_voyage_profile
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND lower(email_contact) = lower(%(email_contact)s)
  AND date_of_birth = %(date_of_birth)s
  AND (
        lower(maritime_account_id) = lower(%(maritime_account_id)s)
        OR maritime_account_id IS NULL
      )
LIMIT 1
"""


QUERY6 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 6 AS match_criteria
FROM customer_voyage_profile
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND lower(email_contact) = lower(%(email_contact)s)
  AND date_of_birth = %(date_of_birth)s
  AND (
        lower(maritime_account_id) = lower(%(maritime_account_id)s)
        OR maritime_account_id IS NULL
      )
ORDER BY most_recent_sailing_date_1 DESC
LIMIT 1
"""


QUERY7 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 7 AS match_criteria
FROM customer_voyage_profile
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND date_of_birth = %(date_of_birth)s
  AND contact_number = toString(%(contact_number)s)
  AND (
        lower(maritime_account_id) = lower(%(maritime_account_id)s)
        OR maritime_account_id IS NULL
      )
LIMIT 1
"""


QUERY8 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 8 AS match_criteria
FROM customer_voyage_profile
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND date_of_birth = %(date_of_birth)s
  AND contact_number = toString(%(contact_number)s)
  AND (
        lower(maritime_account_id) = lower(%(maritime_account_id)s)
        OR maritime_account_id IS NULL
      )
ORDER BY most_recent_sailing_date_1 DESC
LIMIT 1
"""


QUERY9 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 9 AS match_criteria
FROM customer_voyage_profile
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND date_of_birth = %(date_of_birth)s
  AND lower(port_city) = lower(%(port_city)s)
  AND substr(toString(zip_code), 1, 5)
      = substr(toString(%(zip_code)s), 1, 5)
  AND substr(lower(address_line_1), 1, least(length(%(address_line_1)s), 9))
      = substr(lower(%(address_line_1)s), 1, least(length(%(address_line_1)s), 9))
  AND (
        lower(maritime_account_id) = lower(%(maritime_account_id)s)
        OR maritime_account_id IS NULL
      )
LIMIT 1
"""


QUERY10 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 10 AS match_criteria
FROM customer_voyage_profile
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND date_of_birth = %(date_of_birth)s
  AND lower(port_city) = lower(%(port_city)s)
  AND substr(toString(zip_code), 1, 5)
      = substr(toString(%(zip_code)s), 1, 5)
  AND substr(lower(address_line_1), 1, least(length(%(address_line_1)s), 9))
      = substr(lower(%(address_line_1)s), 1, least(length(%(address_line_1)s), 9))
  AND (
        lower(maritime_account_id) = lower(%(maritime_account_id)s)
        OR maritime_account_id IS NULL
      )
ORDER BY most_recent_sailing_date_1 DESC
LIMIT 1
"""


QUERY11 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 11 AS match_criteria
FROM customer_voyage_profile
WHERE lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND lower(email_contact) = lower(%(email_contact)s)
  AND contact_number = toString(%(contact_number)s)
  AND date_of_birth = %(date_of_birth)s
LIMIT 1
"""


QUERY12 = """
SELECT given_name,
surname,
date_of_birth,
maritime_account_id,
email_contact,
contact_number,
most_recent_sailing_date_1,
port_city,
address_line_1,
zip_code,
address_line_2,
membership_start_date_1, 12 AS match_criteria
FROM customer_voyage_profile
WHERE lower(maritime_account_id) = lower(%(maritime_account_id)s)
  AND lower(given_name) = lower(%(given_name)s)
  AND lower(surname) = lower(%(surname)s)
  AND membership_start_date_1 = %(membership_start_date_1)s
ORDER BY most_recent_sailing_date_1 DESC
LIMIT 1
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

# QUERIES = {1: QUERY1, 2: QUERY2}
