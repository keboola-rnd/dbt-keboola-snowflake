{%- materialization test, adapter='keboola_snowflake' -%}

    {% set original_query_tag = set_query_tag() %}
    {% set relations = materialization_test_default() %}
    {% do unset_query_tag(original_query_tag) %}
    {{ return(relations) }}

{%- endmaterialization -%}
