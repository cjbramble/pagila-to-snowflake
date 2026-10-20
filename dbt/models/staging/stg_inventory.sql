select
    inventory_id,
    film_id,
    store_id
from {{ source('raw', 'inventory') }}
