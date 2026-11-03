# 指标口径定义

口径不一致是分析结果互相矛盾的根源。本文件是唯一权威定义，看板与 SQL 均以此为基准。

## 通用规则

- **有效订单**：`order_status NOT IN ('canceled', 'unavailable')`
- **时间基准**：一律使用 `order_purchase_timestamp`（下单时间），不按签收时间归月
- **客户标识**：一律使用 `customer_unique_id`
- **货币**：巴西雷亚尔（R$），不做汇率折算

---

## 1. GMV（商品交易总额）

**定义**：有效订单的支付总额合计，含运费。

```sql
SUM(COALESCE(payment_total, 0))   -- payment_total = 订单全部支付流水之和
```

**口径边界（重要）**
- 含运费，不含退款冲销（数据集无退款数据）
- 剔除 canceled / unavailable
- 存在 1 笔无支付记录的订单，按 0 计入，不影响总量

**衍生**：`delivered_gmv` 仅统计已送达订单，用于区分"成交"与"履约完成"。

---

## 2. 客单价 AOV

```sql
AOV = GMV / 有效订单数
```

不使用 `SUM(payment_total) / COUNT(DISTINCT customer_unique_id)`——那是人均消费，不是客单价。

---

## 3. 复购率

**定义**：已送达订单中，下过 2 单及以上的自然人在全部购买客户中的占比。

```sql
复购率 = COUNT(customer_unique_id WHERE 订单数 > 1) / COUNT(DISTINCT customer_unique_id)
```

**说明**：本数据集复购率仅 3.0%，是数据集特性（以一次性购买为主），不代表平台真实水平，解读时需注明。

---

## 4. RFM 分层

| 维度 | 定义 | 打分方式 |
| --- | --- | --- |
| R（Recency） | 距今最近一次下单的天数 | 按天数降序 `NTILE(5)`，越近分越高 |
| F（Frequency） | 已送达订单数（去重） | 升序 `NTILE(5)` |
| M（Monetary） | 累计支付金额 | 升序 `NTILE(5)` |

基准日 = 全量订单的最大下单时间（固定值，保证不同筛选条件下可比）。

**分层规则（R × M）**

| 分层 | 条件 | 运营含义 |
| --- | --- | --- |
| 高价值活跃 | R≥4 且 M≥4 | 维护为主，做交叉销售 |
| 高价值沉睡 | R≤2 且 M≥4 | 召回优先级最高 |
| 潜力新客 | R≥4 且 M≤2 | 优惠券提升首单→二单 |
| 流失客户 | R≤2 且 M≤2 | 低成本触达或放弃 |
| 一般客户 | 其余 | 常规运营 |

**已知缺陷**：97% 客户只有 1 单，F 恒为 1，该维度实际不参与区分。文档与看板均需注明，避免误导。

---

## 5. 履约漏斗

| 环节 | 判定条件 |
| --- | --- |
| 下单 | 订单存在 |
| 支付通过 | `order_approved_at IS NOT NULL` |
| 交给承运商 | `order_delivered_carrier_date IS NOT NULL` |
| 送达客户 | `order_delivered_customer_date IS NOT NULL` |
| 收到评价 | 已送达且存在评价记录 |

**注意**：漏斗基数包含 canceled 订单的下单环节，但不含"下单前流失"。"收到评价"只统计已送达订单，保证单调递减。

---

## 6. 延迟天数与差评率

```sql
delay_days = DATE_DIFF('day', 承诺送达日期, 实际签收日期)
```

- `delay_days < 0`：提前送达
- `delay_days = 0`：准时
- `delay_days > 0`：迟到天数

**差评率** = 评分 ≤ 2 的订单数 / 有评分订单数。

仅统计 `order_status='delivered'` 且签收时间、评分均非空的订单。

---

## 7. 品类营收

```sql
SUM(order_items.price)   -- 不含运费
```

按 `dim_product.category_en` 汇总，未翻译品类归入 `unknown`。剔除 canceled / unavailable 订单。

**帕累托累计占比**按营收降序累加，用于判断集中度。

---

## 8. 支付分析

- 订单级支付方式：取金额最大的一笔（`arg_max(payment_type, payment_value)`）
- 分期期数：取订单内最大分期数 `max_installments`
- 分期分档：1 期 / 2-3 期 / 4-6 期 / 7 期以上

---

## 口径变更记录

| 日期 | 变更 | 影响 |
| --- | --- | --- |
| 2026-10-28 | 初始版本 | — |
