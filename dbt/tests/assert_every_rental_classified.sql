-- ETL-005: every rental has exactly one row (no rental lost to a join).
{{ config(meta={'requirement': 'ETL-005'}) }}

select
    (select count(*) from {{ ref('stg_rental') }}) as rentals,
    (select count(*) from {{ ref('mart_rental_returns') }}) as classified
where rentals <> classified
