-- Grain: one row per customer with at least one completed order.
select
    customer_id,
    count(*) as completed_order_count,
    sum(amount_cents) as revenue_cents
from {{ ref('stg_orders') }}
where status = 'completed'
group by customer_id
