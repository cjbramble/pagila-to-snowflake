{#- Use the configured schema as-is (STAGING, MARTS) instead of dbt's default
    "<target schema>_<custom schema>" naming; this project has one fixed environment.
    The mutation target prefixes MUT_ so mutated models never replace the real ones. -#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set schema = (custom_schema_name or target.schema) | trim -%}
    {%- if target.name == 'mutation' and not schema.startswith('MUT_') -%}
        MUT_{{ schema }}
    {%- else -%}
        {{ schema }}
    {%- endif -%}
{%- endmacro %}
