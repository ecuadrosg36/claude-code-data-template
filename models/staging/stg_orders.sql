-- Grain: one row per order_id. Monetary values remain integer cents.
select
    cast(order_id as integer) as order_id,
    cast(customer_id as integer) as customer_id,
    cast(order_date as date) as order_date,
    lower(trim(status)) as status,
    cast(amount_cents as bigint) as amount_cents
from {{ ref('raw_orders') }}
