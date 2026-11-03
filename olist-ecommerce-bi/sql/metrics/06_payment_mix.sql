-- 06_payment_mix.sql
-- 口径：订单级支付方式取金额最大的一笔；剔除取消/不可用订单。

CREATE OR REPLACE TABLE metrics.payment_mix AS
WITH base AS (
    SELECT
        COALESCE(main_payment_type, 'unknown') AS payment_type,
        payment_total,
        max_installments
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND payment_total IS NOT NULL
)
SELECT
    payment_type,
    COUNT(*) AS orders,
    ROUND(SUM(payment_total), 2) AS gmv,
    ROUND(AVG(payment_total), 2) AS avg_order_value,
    ROUND(AVG(max_installments), 2) AS avg_installments,
    ROUND(COUNT(*) / SUM(COUNT(*)) OVER (), 4) AS order_share
FROM base
GROUP BY payment_type
ORDER BY orders DESC;

CREATE OR REPLACE TABLE metrics.installment_mix AS
WITH base AS (
    SELECT
        max_installments,
        payment_total
    FROM fact_orders
    WHERE order_status NOT IN ('canceled', 'unavailable')
      AND payment_total IS NOT NULL
      AND max_installments IS NOT NULL
),
bucketed AS (
    SELECT
        CASE
            WHEN max_installments <= 1  THEN '1 期'
            WHEN max_installments <= 3  THEN '2-3 期'
            WHEN max_installments <= 6  THEN '4-6 期'
            ELSE '7 期以上'
        END AS installment_bucket,
        CASE
            WHEN max_installments <= 1  THEN 1
            WHEN max_installments <= 3  THEN 2
            WHEN max_installments <= 6  THEN 3
            ELSE 4
        END AS bucket_order,
        max_installments,
        payment_total
    FROM base
)
SELECT
    installment_bucket,
    bucket_order,
    COUNT(*) AS orders,
    ROUND(AVG(payment_total), 2) AS avg_order_value,
    ROUND(AVG(max_installments), 2) AS avg_installments
FROM bucketed
GROUP BY installment_bucket, bucket_order
ORDER BY bucket_order;
