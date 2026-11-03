-- 04_delivery_vs_review.sql
-- 口径：delay_days = 实际送达日期 - 承诺送达日期，正值代表迟到天数。

CREATE OR REPLACE TABLE metrics.delivery_vs_review AS
WITH base AS (
    SELECT review_score, delay_days
    FROM fact_orders
    WHERE order_status = 'delivered'
      AND delivered_customer_ts IS NOT NULL
      AND review_score IS NOT NULL
),
bucketed AS (
    SELECT
        CASE
            WHEN delay_days < 0                    THEN '提前送达'
            WHEN delay_days = 0                    THEN '准时'
            WHEN delay_days BETWEEN 1 AND 3        THEN '延迟 1-3 天'
            WHEN delay_days BETWEEN 4 AND 7        THEN '延迟 4-7 天'
            WHEN delay_days BETWEEN 8 AND 15       THEN '延迟 8-15 天'
            ELSE '延迟 15 天以上'
        END AS delay_bucket,
        CASE
            WHEN delay_days < 0              THEN 1
            WHEN delay_days = 0              THEN 2
            WHEN delay_days BETWEEN 1 AND 3  THEN 3
            WHEN delay_days BETWEEN 4 AND 7  THEN 4
            WHEN delay_days BETWEEN 8 AND 15 THEN 5
            ELSE 6
        END AS bucket_order,
        review_score
    FROM base
)
SELECT
    delay_bucket,
    bucket_order,
    COUNT(*) AS orders,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END), 4) AS bad_review_rate,
    ROUND(AVG(CASE WHEN review_score = 1 THEN 1.0 ELSE 0.0 END), 4) AS one_star_rate
FROM bucketed
GROUP BY delay_bucket, bucket_order
ORDER BY bucket_order;
