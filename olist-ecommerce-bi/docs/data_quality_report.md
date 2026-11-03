# 数据质量报告

生成时间：2026-10-28 11:56

## 数据规模

- 订单数：99,441
- 订单明细行数：112,650
- 下单时间范围：2016-09-04 21:15:19 ~ 2018-10-17 17:30:18

## 订单状态分布

| 状态 | 订单数 |
| --- | ---: |
| delivered | 96,478 |
| shipped | 1,107 |
| canceled | 625 |
| unavailable | 609 |
| invoiced | 314 |
| processing | 301 |
| created | 5 |
| approved | 2 |

## 质量检查项

| 检查项 | 结果 | 说明 |
| --- | ---: | --- |
| 订单主键唯一 | 0 | orders 中 order_id 不应重复（不为 0 则主键重复）|
| 订单缺少下单时间 | 0 | order_purchase_timestamp 为空的记录无法进入时间分析（记录了缺失量）|
| 客户主键唯一 | 0 | customers 中 customer_id 不应重复（不为 0 则主键重复）|
| 一个客户对应多个 customer_unique_id | 2,997 | customer_id 是订单级标识，customer_unique_id 才是自然人（大于 0 说明识别口径必须用 unique_id）|
| 明细价格为负 | 0 | order_items 中 price / freight_value 出现负值属于脏数据（应为 0）|
| 明细孤儿订单 | 0 | order_items.order_id 无法关联到 orders（应为 0）|
| 明细孤儿商品 | 0 | order_items.product_id 无法关联到 products（应为 0）|
| 订单无支付记录 | 1 | 部分订单没有 payments 记录，计算 GMV 时必须处理（记录了缺失量）|
| 商品类目缺失 | 610 | products.category_pt 为空，需归入 unknown（记录了缺失量）|
| 评分一单多条 | 547 | reviews 中存在同一订单多条评价，事实表需去重（记录了重复订单数）|
| 已交付但无签收时间 | 8 | status=delivered 却缺 delivered_customer_ts，履约分析需排除（记录了缺失量）|
