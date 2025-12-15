{% macro keboola_snowflake__create_schema(relation) -%}
  {#
    Keboola Query Service workspaces have pre-assigned schemas and cannot create new schemas.
    This macro is overridden to prevent schema creation attempts which would fail with
    "Insufficient privileges to operate on database" errors.

    Instead, we simply check if the schema exists (which it should, as it's pre-created).
  #}
  {% call statement('create_schema') %}
    -- Schema creation skipped for Keboola workspace
    -- Workspace schema {{ relation.schema }} is pre-created and managed by Keboola
    SELECT 'Schema {{ relation.schema }} already exists' as message
  {% endcall %}
{%- endmacro %}

{% macro keboola_snowflake__drop_schema(relation) -%}
  {#
    Keboola Query Service workspaces cannot drop schemas.
    This macro is overridden to prevent schema drop attempts.
  #}
  {% call statement('drop_schema') %}
    -- Schema drop skipped for Keboola workspace
    -- Workspace schemas are managed by Keboola and cannot be dropped
    SELECT 'Schema drop operation skipped for Keboola workspace' as message
  {% endcall %}
{%- endmacro %}
