-- 01_dims.sql
-- 维度表：星型模型的描述性属性

CREATE OR REPLACE TABLE dim_customer AS
SELECT
    customer_id,
    customer_unique_id,
    zip_prefix,
    city,
    state
FROM staging.customers;

CREATE OR REPLACE TABLE dim_product AS
SELECT
    p.product_id,
    COALESCE(t.category_en, 'unknown') AS category_en,
    COALESCE(p.category_pt, 'unknown') AS category_pt,
    p.weight_g,
    p.length_cm,
    p.height_cm,
    p.width_cm,
    p.photos_qty
FROM staging.products p
LEFT JOIN staging.category_translation t ON p.category_pt = t.category_pt;

CREATE OR REPLACE TABLE dim_seller AS
SELECT
    seller_id,
    zip_prefix,
    city,
    state
FROM staging.sellers;

CREATE OR REPLACE TABLE dim_date AS
SELECT
    CAST(d AS DATE) AS date,
    EXTRACT(year    FROM d) AS year,
    EXTRACT(month   FROM d) AS month,
    EXTRACT(quarter FROM d) AS quarter,
    EXTRACT(dayofweek FROM d) AS day_of_week,
    STRFTIME(d, '%Y-%m') AS year_month
FROM generate_series(DATE '2016-01-01', DATE '2019-01-01', INTERVAL 1 DAY) AS t(d);
