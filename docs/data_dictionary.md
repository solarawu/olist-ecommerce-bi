# 数据字典

数据源：Kaggle *Brazilian E-Commerce Public Dataset by Olist*，巴西电商平台 2016-09 ~ 2018-10 的真实订单数据。

## 1. 源数据表

| 文件 | 行数 | 粒度 | 主键 | 说明 |
| --- | ---: | --- | --- | --- |
| `olist_orders_dataset.csv` | 99,441 | 订单 | `order_id` | 订单状态与 4 个履约时间节点 |
| `olist_order_items_dataset.csv` | 112,650 | 订单明细 | `order_id + order_item_id` | 商品、卖家、单价、运费 |
| `olist_order_payments_dataset.csv` | 103,886 | 支付流水 | `order_id + payment_sequential` | 一个订单可多笔支付，聚合后覆盖 99,440 个订单 |
| `olist_order_reviews_dataset.csv` | 99,224 | 评价 | `review_id` | 一个订单可能有多条评价 |
| `olist_customers_dataset.csv` | 99,441 | 订单级客户 | `customer_id` | 含自然人标识 `customer_unique_id` |
| `olist_products_dataset.csv` | 32,951 | 商品 | `product_id` | 品类为葡萄牙语 |
| `olist_sellers_dataset.csv` | 3,095 | 卖家 | `seller_id` | 城市 / 州 |
| `product_category_name_translation.csv` | 70 | 品类映射 | `product_category_name` | 葡语 -> 英语 |
| `olist_geolocation_dataset.csv` | 1,000,163 | 邮编前缀 | 无 | 未纳入模型，见文末说明 |

## 2. 关键字段说明

### orders

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `order_status` | string | delivered / shipped / canceled / unavailable / invoiced / processing / created / approved |
| `order_purchase_timestamp` | timestamp | 下单时间，所有时间分析的基准 |
| `order_approved_at` | timestamp | 支付通过时间 |
| `order_delivered_carrier_date` | timestamp | 交给承运商时间 |
| `order_delivered_customer_date` | timestamp | 客户签收时间 |
| `order_estimated_delivery_date` | timestamp | 承诺送达日期 |

### customers

| 字段 | 说明 |
| --- | --- |
| `customer_id` | **订单级**标识，每笔订单一个新值 |
| `customer_unique_id` | **自然人**标识，跨订单稳定 —— 所有用户分析必须用它 |

### order_items

| 字段 | 说明 |
| --- | --- |
| `price` | 商品单价（不含运费） |
| `freight_value` | 运费 |
| `shipping_limit_date` | 卖家发货截止时间 |

## 3. 已知数据问题

| 问题 | 影响 | 处理方式 |
| --- | --- | --- |
| `product_category_name_translation.csv` 带 BOM | 列名污染 | 按列位读取（`header=false, skip=1`） |
| `review_comment_message` 含换行 | 行数统计失真 | 用 `read_csv_auto` 按引号解析，实际 99,224 行 |
| 610 个商品品类为空 | 品类汇总出现 null | 统一归入 `unknown` |
| 547 个订单有多条评价 | 一单多评 | 事实表取 `review_creation_date` 最新一条 |
| 1 个订单无支付记录 | GMV 汇总出现 null | `COALESCE(payment_total, 0)` |
| 8 个 delivered 订单无签收时间 | 履约分析分母失真 | 履约分析显式排除 |
| 2,997 个自然人对应多个 customer_id | 用户数被高估 | 统一按 `customer_unique_id` 聚合 |

## 4. 派生表

| 表 | 粒度 | 说明 |
| --- | --- | --- |
| `dim_customer` | 自然人 | 客户属性 |
| `dim_product` | 商品 | 品类（英/葡）、尺寸、重量 |
| `dim_seller` | 卖家 | 城市、州 |
| `dim_date` | 日 | 2016-01-01 ~ 2019-01-01 |
| `fact_orders` | 订单 | 履约节点、支付、评分、延迟天数 |
| `fact_order_items` | 订单明细 | 商品与卖家维度 |

`fact_orders` 关键计算字段：

- `delivery_days` = 签收时间 - 下单时间（自然日）
- `delay_days` = 签收时间 - 承诺送达日期，**正值代表迟到**

## 5. 未使用的数据

`olist_geolocation_dataset`（100 万行邮编坐标）未纳入模型。原因：本项目的地理分析需求（州级对比）已由 `customer_state` 满足，引入邮编级坐标表需要额外的聚合与去重逻辑，对结论没有增量价值。
