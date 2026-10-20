{#- Use the configured schema as-is (STAGING, MARTS) instead of dbt's default
    "<target schema>_<custom schema>" naming; this project has one fixed environment. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ (custom_schema_name or target.schema) | trim }}
{%- endmacro %}
