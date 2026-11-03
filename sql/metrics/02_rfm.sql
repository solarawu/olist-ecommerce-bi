-- 02_rfm.sql
-- 口径：仅统计已送达订单；客户粒度用 customer_unique_id（自然人），不是 customer_id（订单级）。
-- 说明：本数据集 90% 以上客户只下过 1 单，F 维度几乎无区分度，实际分层主要看 R 与 M。

CREATE OR REPLACE TABLE metrics.rfm AS
WITH delivered_orders AS (
    SELECT
        customer_unique_id,
        order_id,
        order_purchase_ts,
        COALESCE(payment_total, 0) AS revenue
    FROM fact_orders
    WHERE order_status = 'delivered'
      AND customer_unique_id IS NOT NULL
      AND order_purchase_ts IS NOT NULL
),
ref AS (
    SELECT MAX(order_purchase_ts) AS ref_ts
    FROM fact_orders
    WHERE order_purchase_ts IS NOT NULL
),
customer_level AS (
    SELECT
        customer_unique_id,
        MAX(order_purchase_ts) AS last_order_ts,
        COUNT(DISTINCT order_id) AS frequency,
        SUM(revenue) AS monetary,
        DATE_DIFF('day', MAX(order_purchase_ts), (SELECT ref_ts FROM ref)) AS recency_days
    FROM delivered_orders
    GROUP BY customer_unique_id
),
scored AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY recency_days DESC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency)          AS f_score,
        NTILE(5) OVER (ORDER BY monetary)           AS m_score
    FROM customer_level
)
SELECT
    customer_unique_id,
    last_order_ts,
    recency_days,
    frequency,
    ROUND(monetary, 2) AS monetary,
    r_score,
    f_score,
    m_score,
    CASE
        WHEN r_score >= 4 AND m_score >= 4 THEN '高价值活跃'
        WHEN r_score <= 2 AND m_score >= 4 THEN '高价值沉睡'
        WHEN r_score >= 4 AND m_score <= 2 THEN '潜力新客'
        WHEN r_score <= 2 AND m_score <= 2 THEN '流失客户'
        ELSE '一般客户'
    END AS segment
FROM scored;
