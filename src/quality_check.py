"""数据质量检查：跑完 staging 层后可独立执行。

输出：控制台报告 + docs/data_quality_report.md

用法：
    python -m src.quality_check
"""

from __future__ import annotations

from datetime import datetime

from src.config import BASE_DIR, get_connection

# (检查项, 说明, 返回单个数值的 SQL, 判定阈值说明)
CHECKS = [
    (
        "订单主键唯一",
        "orders 中 order_id 不应重复",
        "SELECT COUNT(*) - COUNT(DISTINCT order_id) FROM staging.orders",
        "不为 0 则主键重复",
    ),
    (
        "订单缺少下单时间",
        "order_purchase_timestamp 为空的记录无法进入时间分析",
        "SELECT COUNT(*) FROM staging.orders WHERE order_purchase_ts IS NULL",
        "记录了缺失量",
    ),
    (
        "客户主键唯一",
        "customers 中 customer_id 不应重复",
        "SELECT COUNT(*) - COUNT(DISTINCT customer_id) FROM staging.customers",
        "不为 0 则主键重复",
    ),
    (
        "一个客户对应多个 customer_unique_id",
        "customer_id 是订单级标识，customer_unique_id 才是自然人",
        "SELECT COUNT(*) FROM (SELECT customer_unique_id FROM staging.customers GROUP BY 1 HAVING COUNT(DISTINCT customer_id) > 1)",
        "大于 0 说明识别口径必须用 unique_id",
    ),
    (
        "明细价格为负",
        "order_items 中 price / freight_value 出现负值属于脏数据",
        "SELECT COUNT(*) FROM staging.order_items WHERE price < 0 OR freight_value < 0",
        "应为 0",
    ),
    (
        "明细孤儿订单",
        "order_items.order_id 无法关联到 orders",
        "SELECT COUNT(*) FROM staging.order_items i ANTI JOIN staging.orders o ON i.order_id = o.order_id",
        "应为 0",
    ),
    (
        "明细孤儿商品",
        "order_items.product_id 无法关联到 products",
        "SELECT COUNT(*) FROM staging.order_items i ANTI JOIN staging.products p ON i.product_id = p.product_id",
        "应为 0",
    ),
    (
        "订单无支付记录",
        "部分订单没有 payments 记录，计算 GMV 时必须处理",
        "SELECT COUNT(*) FROM staging.orders o ANTI JOIN staging.payments p ON o.order_id = p.order_id",
        "记录了缺失量",
    ),
    (
        "商品类目缺失",
        "products.category_pt 为空，需归入 unknown",
        "SELECT COUNT(*) FROM staging.products WHERE category_pt IS NULL",
        "记录了缺失量",
    ),
    (
        "评分一单多条",
        "reviews 中存在同一订单多条评价，事实表需去重",
        "SELECT COUNT(*) FROM (SELECT order_id FROM staging.review_raw GROUP BY 1 HAVING COUNT(*) > 1)",
        "记录了重复订单数",
    ),
    (
        "已交付但无签收时间",
        "status=delivered 却缺 delivered_customer_ts，履约分析需排除",
        "SELECT COUNT(*) FROM staging.orders WHERE order_status = 'delivered' AND delivered_customer_ts IS NULL",
        "记录了缺失量",
    ),
]


def run() -> str:
    con = get_connection()
    try:
        rows = []
        for name, desc, sql, threshold in CHECKS:
            value = con.execute(sql).fetchone()[0]
            rows.append((name, desc, int(value), threshold))

        total_orders = con.execute("SELECT COUNT(*) FROM staging.orders").fetchone()[0]
        total_items = con.execute("SELECT COUNT(*) FROM staging.order_items").fetchone()[0]
        date_range = con.execute(
            "SELECT MIN(order_purchase_ts), MAX(order_purchase_ts) FROM staging.orders"
        ).fetchone()
        status_dist = con.execute(
            "SELECT order_status, COUNT(*) FROM staging.orders GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
    finally:
        con.close()

    lines = [
        "# 数据质量报告",
        "",
        f"生成时间：{datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## 数据规模",
        "",
        f"- 订单数：{total_orders:,}",
        f"- 订单明细行数：{total_items:,}",
        f"- 下单时间范围：{date_range[0]} ~ {date_range[1]}",
        "",
        "## 订单状态分布",
        "",
        "| 状态 | 订单数 |",
        "| --- | ---: |",
    ]
    lines += [f"| {s} | {c:,} |" for s, c in status_dist]
    lines += [
        "",
        "## 质量检查项",
        "",
        "| 检查项 | 结果 | 说明 |",
        "| --- | ---: | --- |",
    ]
    for name, desc, value, threshold in rows:
        lines.append(f"| {name} | {value:,} | {desc}（{threshold}）|")

    report = "\n".join(lines) + "\n"
    out_path = BASE_DIR / "docs" / "data_quality_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")

    print(report)
    print(f"报告已写入：{out_path}")
    return report


if __name__ == "__main__":
    run()
