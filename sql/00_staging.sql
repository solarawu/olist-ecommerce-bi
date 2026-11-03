-- 00_staging.sql
-- 原始 CSV -> staging 层：只做字段重命名与类型转换，不做业务过滤。

CREATE SCHEMA IF NOT EXISTS staging;

CREATE OR REPLACE TABLE staging.orders AS
SELECT
    order_id,
    customer_id,
    order_status,
    TRY_CAST(order_purchase_timestamp   AS TIMESTAMP) AS order_purchase_ts,
    TRY_CAST(order_approved_at          AS TIMESTAMP) AS order_approved_ts,
    TRY_CAST(order_delivered_carrier_date AS TIMESTAMP) AS delivered_carrier_ts,
    TRY_CAST(order_delivered_customer_date AS TIMESTAMP) AS delivered_customer_ts,
    TRY_CAST(order_estimated_delivery_date AS TIMESTAMP) AS estimated_delivery_ts
FROM read_csv_auto('{{OLIST_DIR}}/olist_orders_dataset.csv', header = true);

CREATE OR REPLACE TABLE staging.customers AS
SELECT
    customer_id,
    customer_unique_id,
    try_cast(customer_zip_code_prefix AS INTEGER) AS zip_prefix,
    customer_city AS city,
    customer_state AS state
FROM read_csv_auto('{{OLIST_DIR}}/olist_customers_dataset.csv', header = true);

CREATE OR REPLACE TABLE staging.order_items AS
SELECT
    order_id,
    try_cast(order_item_id AS INTEGER) AS order_item_id,
    product_id,
    seller_id,
    TRY_CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_ts,
    try_cast(price AS DOUBLE) AS price,
    try_cast(freight_value AS DOUBLE) AS freight_value
FROM read_csv_auto('{{OLIST_DIR}}/olist_order_items_dataset.csv', header = true);

CREATE OR REPLACE TABLE staging.payments AS
SELECT
    order_id,
    SUM(try_cast(payment_value AS DOUBLE)) AS payment_total,
    MAX(try_cast(payment_installments AS INTEGER)) AS max_installments,
    COUNT(*) AS payment_count,
    arg_max(payment_type, try_cast(payment_value AS DOUBLE)) AS main_payment_type
FROM read_csv_auto('{{OLIST_DIR}}/olist_order_payments_dataset.csv', header = true)
GROUP BY order_id;

-- 保留原始评价明细，供质量检查统计「一单多评」
CREATE OR REPLACE TABLE staging.review_raw AS
SELECT
    review_id,
    order_id,
    try_cast(review_score AS INTEGER) AS review_score,
    TRY_CAST(review_creation_date AS TIMESTAMP) AS review_created_ts
FROM read_csv_auto('{{OLIST_DIR}}/olist_order_reviews_dataset.csv', header = true);

-- 事实表用最新一条评价
CREATE OR REPLACE TABLE staging.reviews AS
SELECT order_id, review_score, review_created_ts
FROM (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY review_created_ts DESC) AS rn
    FROM staging.review_raw
)
WHERE rn = 1;

CREATE OR REPLACE TABLE staging.products AS
SELECT
    product_id,
    product_category_name AS category_pt,
    try_cast(product_weight_g AS INTEGER) AS weight_g,
    try_cast(product_length_cm AS INTEGER) AS length_cm,
    try_cast(product_height_cm AS INTEGER) AS height_cm,
    try_cast(product_width_cm AS INTEGER) AS width_cm,
    try_cast(product_photos_qty AS INTEGER) AS photos_qty
FROM read_csv_auto('{{OLIST_DIR}}/olist_products_dataset.csv', header = true);

CREATE OR REPLACE TABLE staging.sellers AS
SELECT
    seller_id,
    try_cast(seller_zip_code_prefix AS INTEGER) AS zip_prefix,
    seller_city AS city,
    seller_state AS state
FROM read_csv_auto('{{OLIST_DIR}}/olist_sellers_dataset.csv', header = true);

-- 源文件带 BOM，按列位读取避免列名污染
CREATE OR REPLACE TABLE staging.category_translation AS
SELECT column0 AS category_pt, column1 AS category_en
FROM read_csv(
    '{{OLIST_DIR}}/product_category_name_translation.csv',
    header = false,
    skip = 1,
    columns = {'column0': 'VARCHAR', 'column1': 'VARCHAR'}
);

-- 订单级明细汇总，供 fact_orders 使用
CREATE OR REPLACE TABLE staging.order_item_totals AS
SELECT
    order_id,
    COUNT(*) AS item_count,
    SUM(price) AS item_revenue,
    SUM(freight_value) AS freight_total
FROM staging.order_items
GROUP BY order_id;
