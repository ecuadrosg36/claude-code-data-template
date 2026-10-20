-- Return violations: a full outer join catches missing and unexpected customers.
with expected as (
    select customer_id, count(*) as orders, sum(amount_cents) as cents
    from {{ ref('stg_orders') }}
    where status = 'completed'
    group by customer_id
)
select coalesce(e.customer_id, f.customer_id) as customer_id
from expected e
full outer join {{ ref('fct_customer_orders') }} f using (customer_id)
where e.customer_id is null or f.customer_id is null
   or e.orders != f.completed_order_count or e.cents != f.revenue_cents
