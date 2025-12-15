{% macro keboola_snowflake__get_replace_table_sql(relation, sql) %}
    {{ keboola_snowflake__create_table_as(False, relation, sql) }}
{% endmacro %}
