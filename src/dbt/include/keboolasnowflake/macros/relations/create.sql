{% macro keboola_snowflake__get_create_sql(relation, sql) %}

    {% if relation.is_dynamic_table %}
        {{ keboola_snowflake__get_create_dynamic_table_as_sql(relation, sql) }}

    {% else %}
        {{ default__get_create_sql(relation, sql) }}

    {% endif %}

{% endmacro %}
