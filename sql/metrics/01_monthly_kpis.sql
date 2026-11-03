-- 01_monthly_kpis.sql
-- 口径：GMV 取订单支付总额，剔除 canceled / unavailable 订单；不含退款冲销。

CREATE OR REPLACE TABLE metrics.monthly_kpis AS
WITH base AS (
    SELECT *
    FROM fact_orders
    WHERE order_purchase_ts IS NOT NULL
      AND order_status NOT IN ('canceled', 'unavailable')
),
agg AS (
    SELECT
        purchase_month,
        COUNT(*) AS orders,
        COUNT(DISTINCT customer_unique_id) AS active_customers,
        ROUND(SUM(COALESCE(payment_total, 0)), 2) AS gmv,
        ROUND(SUM(COALESCE(payment_total, 0)) / NULLIF(COUNT(*), 0), 2) AS aov,
        ROUND(AVG(review_score), 2) AS avg_review_score,
        ROUND(SUM(CASE WHEN order_status = 'delivered' THEN COALESCE(payment_total, 0) ELSE 0 END), 2) AS delivered_gmv,
        SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders
    FROM base
    GROUP BY purchase_month
)
SELECT
    m.*,
    ROUND(
        (gmv - LAG(gmv) OVER (ORDER BY purchase_month))
        / NULLIF(LAG(gmv) OVER (ORDER BY purchase_month), 0),
        4
    ) AS gmv_mom
FROM agg m
ORDER BY purchase_month;
