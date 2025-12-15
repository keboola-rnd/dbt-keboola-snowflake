{% macro keboola_snowflake__get_replace_view_sql(relation, sql) %}
    {{ keboola_snowflake__create_view_as(relation, sql) }}
{% endmacro %}
