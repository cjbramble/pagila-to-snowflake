# Source profile: schema `public`

PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2), server timezone `Etc/UTC`.

## Relations (16 tables, partitions folded into their parent)

| relation | kind | partitions | rows |
|---|---|---|---|
| rental_by_category | materialized view |  | not populated |
| payment | partitioned table | 55 | 51061 |
| actor | table |  | 200 |
| address | table |  | 1003 |
| category | table |  | 16 |
| city | table |  | 600 |
| country | table |  | 109 |
| customer | table |  | 999 |
| film | table |  | 1000 |
| film_actor | table |  | 5462 |
| film_category | table |  | 2367 |
| film_embedding | table |  | 1000 |
| inventory | table |  | 4581 |
| language | table |  | 6 |
| rental | table |  | 51805 |
| staff | table |  | 1500 |
| store | table |  | 500 |
| actor_info | view |  | 200 |
| customer_list | view |  | 999 |
| film_list | view |  | 2360 |
| nicer_but_slower_film_list | view |  | 2360 |
| sales_by_film_category | view |  | 16 |
| sales_by_store | view |  | 2 |
| staff_list | view |  | 1500 |

## Non-trivial columns (35 of 94)

Trivial and omitted: bigint, boolean, date, integer, smallint, text with no special default.

| table | column | type | not null | notes |
|---|---|---|---|---|
| actor | last_update | timestamp with time zone | yes | default now() |
| address | last_update | timestamp with time zone | yes | default now() |
| category | last_update | timestamp with time zone | yes | default now() |
| city | last_update | timestamp with time zone | yes | default now() |
| country | last_update | timestamp with time zone | yes | default now() |
| customer | activebool | boolean | yes | default true |
| customer | create_date | date | yes | default CURRENT_DATE |
| customer | last_update | timestamp with time zone |  | default now() |
| customer | uuid | uuid | yes | default uuidv7() |
| film | release_year | year |  | domain over integer |
| film | rental_duration | smallint | yes | default 3 |
| film | rental_rate | numeric(4,2) | yes | default 4.99 |
| film | replacement_cost | numeric(5,2) | yes | default 19.99 |
| film | rating | mpaa_rating |  | enum; default 'G'::mpaa_rating |
| film | last_update | timestamp with time zone | yes | default now() |
| film | special_features | text[] |  | array |
| film | fulltext | tsvector | yes |  |
| film | length_hours | numeric(4,2) |  | generated virtual: round(((length)::numeric / 60.0), 2) |
| film_actor | last_update | timestamp with time zone | yes | default now() |
| film_category | last_update | timestamp with time zone | yes | default now() |
| film_embedding | embedding | vector(20) | yes |  |
| film_embedding | last_update | timestamp with time zone | yes | default now() |
| inventory | last_update | timestamp with time zone | yes | default now() |
| language | last_update | timestamp with time zone | yes | default now() |
| payment | amount | numeric(5,2) | yes |  |
| payment | payment_date | timestamp with time zone | yes |  |
| payment | uuid | uuid | yes | default uuidv7() |
| rental | rental_date | timestamp with time zone | yes |  |
| rental | return_date | timestamp with time zone |  |  |
| rental | last_update | timestamp with time zone | yes | default now() |
| rental | uuid | uuid | yes | default uuidv7() |
| staff | active | boolean | yes | default true |
| staff | last_update | timestamp with time zone | yes | default now() |
| staff | picture | bytea |  |  |
| store | last_update | timestamp with time zone | yes | default now() |

## Enums

| type | labels |
|---|---|
| mpaa_rating | G, PG, PG-13, R, NC-17 |

## Domains

| domain | base type | not null | constraints |
|---|---|---|---|
| bıgınt | bigint | False |  |
| year | integer | False | CHECK (((VALUE >= 1901) AND (VALUE <= 2155))) |
