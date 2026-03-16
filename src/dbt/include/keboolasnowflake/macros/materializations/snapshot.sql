{% materialization snapshot, adapter='keboola_snowflake' %}
    {% set original_query_tag = set_query_tag() %}
    {% set relations = materialization_snapshot_default() %}

    {% do unset_query_tag(original_query_tag) %}

    {{ return(relations) }}
{% endmaterialization %}


{#
  Override: create staging table as TRANSIENT (not TEMPORARY) so it persists
  across multiple Query Service API calls which run in separate Snowflake sessions.
  The default dbt macro uses TEMPORARY which is session-scoped.
#}
{% macro keboola_snowflake__build_snapshot_staging_table(strategy, sql, target_relation) %}
    {% set temp_relation = make_temp_relation(target_relation) %}
    {% set select = snapshot_staging_table(strategy, sql, target_relation) %}

    {% call statement('build_snapshot_staging_relation') %}
        {{ create_table_as(False, temp_relation, select) }}
    {% endcall %}

    {% do return(temp_relation) %}
{% endmacro %}


{#
  Override: explicitly drop the staging transient table after snapshot completes.
  Required because transient tables don't auto-drop at session end (unlike TEMPORARY).
#}
{% macro keboola_snowflake__post_snapshot(staging_relation) %}
    {% call statement('post_snapshot') %}
        {{ drop_relation_if_exists(staging_relation) }}
    {% endcall %}
{% endmacro %}
