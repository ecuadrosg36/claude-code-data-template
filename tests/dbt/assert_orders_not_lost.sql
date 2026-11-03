-- Reconciliation: every staged order must reach the mart. Returns rows (= fails) if any order is lost
-- or duplicated, e.g. after someone changes the LEFT JOIN to an INNER JOIN.
select 'stg_orders' as layer, count(*) as orders from {{ ref('stg_orders') }}
having count(*) <> (select count(*) from {{ ref('fct_orders') }})
