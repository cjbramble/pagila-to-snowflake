select
    film_id,
    title,
    rental_duration,
    rental_rate,
    replacement_cost
from {{ source('raw', 'film') }}
