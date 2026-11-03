-- 05_category_pareto.sql
-- 口径：品类营收按订单明细 price 汇总，剔除取消/不可用订单，不含运费。

CREATE OR REPLACE TABLE metrics.category_revenue AS
WITH base AS (
    SELECT
        COALESCE(p.category_en, 'unknown') AS category,
        SUM(foi.price) AS revenue,
        COUNT(DISTINCT foi.order_id) AS orders,
        COUNT(*) AS items
    FROM fact_order_items foi
    JOIN fact_orders fo    ON foi.order_id  = fo.order_id
    LEFT JOIN dim_product p ON foi.product_id = p.product_id
    WHERE fo.order_status NOT IN ('canceled', 'unavailable')
    GROUP BY 1
),
ranked AS (
    SELECT *, ROW_NUMBER() OVER (ORDER BY revenue DESC) AS rank
    FROM base
)
SELECT
    category,
    rank,
    ROUND(revenue, 2) AS revenue,
    orders,
    items,
    ROUND(revenue / SUM(revenue) OVER (), 4) AS revenue_share,
    ROUND(
        SUM(revenue) OVER (ORDER BY revenue DESC ROWS UNBOUNDED PRECEDING)
        / SUM(revenue) OVER (),
        4
    ) AS cumulative_share
FROM ranked
ORDER BY rank;
