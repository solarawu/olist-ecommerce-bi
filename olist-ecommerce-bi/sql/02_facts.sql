-- 02_facts.sql
-- 事实表：订单粒度 + 订单明细粒度

CREATE OR REPLACE TABLE fact_orders AS
SELECT
    o.order_id,
    c.customer_unique_id,
    c.state AS customer_state,
    o.order_status,
    o.order_purchase_ts,
    o.order_approved_ts,
    o.delivered_carrier_ts,
    CAST(o.order_purchase_ts AS DATE) AS purchase_date,
    STRFTIME(o.order_purchase_ts, '%Y-%m') AS purchase_month,
    i.item_count,
    i.item_revenue,
    i.freight_total,
    p.payment_total,
    p.max_installments,
    p.main_payment_type,
    r.review_score,
    o.delivered_customer_ts,
    o.estimated_delivery_ts,
    DATE_DIFF('day', o.order_purchase_ts, o.delivered_customer_ts)     AS delivery_days,
    DATE_DIFF('day', o.estimated_delivery_ts, o.delivered_customer_ts) AS delay_days
FROM staging.orders o
LEFT JOIN dim_customer c          ON o.customer_id = c.customer_id
LEFT JOIN staging.order_item_totals i ON o.order_id = i.order_id
LEFT JOIN staging.payments p      ON o.order_id = p.order_id
LEFT JOIN staging.reviews r       ON o.order_id = r.order_id;

CREATE OR REPLACE TABLE fact_order_items AS
SELECT
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    o.order_purchase_ts,
    CAST(o.order_purchase_ts AS DATE) AS purchase_date,
    o.order_status,
    oi.price,
    oi.freight_value
FROM staging.order_items oi
JOIN staging.orders o ON oi.order_id = o.order_id;
