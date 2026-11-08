{#
  Custom generic dbt tests implementing GridShield's data validation checks.

  dbt ships `not_null` and `unique` as built-ins (used directly in
  schema.yml for the NULL-values check). The macros below cover the
  remaining checks GridShield's methodology requires: duplicate
  timestamps, missing rows, schema mismatch, invalid numeric ranges,
  wrong datatype, future timestamps, and freshness violations. GridShield
  intentionally avoids depending on dbt_utils here to keep this project
  installable with `dbt run` alone, no `dbt deps` / network access needed.
#}

{% test no_duplicate_timestamps(model, column_name) %}
{#- Fails (returns >0 rows) if any value of `column_name` appears more than once. -#}
SELECT {{ column_name }}, COUNT(*) AS occurrence_count
FROM {{ model }}
GROUP BY {{ column_name }}
HAVING COUNT(*) > 1
{% endtest %}


{% test min_row_count(model, min_rows) %}
{#- Fails if the model has fewer than `min_rows` rows (detects missing rows). -#}
SELECT COUNT(*) AS actual_row_count
FROM {{ model }}
HAVING COUNT(*) < {{ min_rows }}
{% endtest %}


{% test expected_columns(model, column_list) %}
{#- Fails if the model's actual columns don't exactly match `column_list` (detects schema mismatch). -#}
{% set relation_columns = adapter.get_columns_in_relation(model) | map(attribute='name') | list %}
{% set missing = column_list | reject('in', relation_columns) | list %}
{% set extra = relation_columns | reject('in', column_list) | list %}
{% if missing or extra %}
SELECT
    '{{ missing | join(", ") }}' AS missing_columns,
    '{{ extra | join(", ") }}' AS extra_columns
{% else %}
SELECT 1 AS ok WHERE FALSE
{% endif %}
{% endtest %}


{% test column_type(model, column_name, expected_type) %}
{#- Fails if `column_name`'s actual dtype does not contain `expected_type` (detects wrong datatype).
   Uses a `namespace()` because plain `{% set %}` inside a `{% for %}` loop is
   scoped to that iteration in Jinja2 and would not persist outside the loop. -#}
{% set ns = namespace(actual_type=none) %}
{% for col in adapter.get_columns_in_relation(model) %}
  {% if col.name == column_name %}
    {% set ns.actual_type = col.dtype %}
  {% endif %}
{% endfor %}
{% if ns.actual_type is none or expected_type.lower() not in ns.actual_type.lower() %}
SELECT '{{ column_name }}' AS column_name, '{{ ns.actual_type }}' AS actual_type, '{{ expected_type }}' AS expected_type
{% else %}
SELECT 1 AS ok WHERE FALSE
{% endif %}
{% endtest %}


{% test accepted_range(model, column_name, min_value, max_value) %}
{#- Fails (returns offending rows) if `column_name` falls outside [min_value, max_value] (detects invalid numeric ranges). -#}
SELECT *
FROM {{ model }}
WHERE {{ column_name }} IS NOT NULL
  AND ({{ column_name }} < {{ min_value }} OR {{ column_name }} > {{ max_value }})
{% endtest %}


{% test no_future_timestamps(model, column_name) %}
{#- Fails if any `column_name` value is later than the current time (detects future timestamps). -#}
SELECT *
FROM {{ model }}
WHERE CAST({{ column_name }} AS TIMESTAMP) > current_timestamp
{% endtest %}


{% test freshness(model, column_name, max_age_hours) %}
{#- Fails if the most recent `column_name` value is older than `max_age_hours` (detects freshness violations). -#}
SELECT MAX(CAST({{ column_name }} AS TIMESTAMP)) AS latest_timestamp
FROM {{ model }}
HAVING MAX(CAST({{ column_name }} AS TIMESTAMP)) < current_timestamp - INTERVAL '{{ max_age_hours }} hours'
{% endtest %}
