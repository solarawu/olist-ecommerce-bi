-- 03_funnel.sql
-- 口径：以全部下单订单为基数，按各环节时间/状态字段是否落库判断是否走完。
-- 「收到评价」只统计已送达订单，保证漏斗单调递减。

CREATE OR REPLACE TABLE metrics.funnel AS
WITH s AS (
    SELECT
        COUNT(*) AS placed,
        SUM(CASE WHEN order_approved_ts    IS NOT NULL THEN 1 ELSE 0 END) AS approved,
        SUM(CASE WHEN delivered_carrier_ts IS NOT NULL THEN 1 ELSE 0 END) AS shipped,
        SUM(CASE WHEN delivered_customer_ts IS NOT NULL THEN 1 ELSE 0 END) AS delivered,
        SUM(CASE WHEN order_status = 'canceled'    THEN 1 ELSE 0 END) AS canceled,
        SUM(CASE WHEN order_status = 'unavailable' THEN 1 ELSE 0 END) AS unavailable
    FROM staging.orders
),
reviewed AS (
    SELECT COUNT(*) AS n
    FROM staging.orders o
    JOIN staging.reviews r ON o.order_id = r.order_id
    WHERE o.delivered_customer_ts IS NOT NULL
),
steps AS (
    SELECT 1 AS step_order, '下单'       AS step, placed AS orders FROM s
    UNION ALL SELECT 2, '支付通过',   approved  FROM s
    UNION ALL SELECT 3, '交给承运商', shipped   FROM s
    UNION ALL SELECT 4, '送达客户',   delivered FROM s
    UNION ALL SELECT 5, '收到评价',   (SELECT n FROM reviewed)
)
SELECT
    step_order,
    step,
    orders,
    ROUND(orders::DOUBLE / (SELECT placed FROM s), 4) AS rate_of_placed,
    ROUND(orders::DOUBLE / LAG(orders) OVER (ORDER BY step_order), 4) AS rate_of_prev
FROM steps
ORDER BY step_order;
