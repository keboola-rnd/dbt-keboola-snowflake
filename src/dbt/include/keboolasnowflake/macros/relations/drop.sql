{% macro keboola_snowflake__get_drop_sql(relation) %}

    {% if relation.is_dynamic_table %}
        {{ keboola_snowflake__get_drop_dynamic_table_sql(relation) }}

    {% else %}
        {{ default__get_drop_sql(relation) }}

    {% endif %}

{% endmacro %}
