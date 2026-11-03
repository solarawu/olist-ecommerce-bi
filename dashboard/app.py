"""Olist 电商经营分析看板。

运行：
    streamlit run dashboard/app.py
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "warehouse" / "olist.duckdb"

BRAND = "#4B3FE3"
BRAND_LIGHT = "#A9AEFF"
ACCENT = "#22A5F7"
GRID = "rgba(0,0,0,0.08)"

st.set_page_config(page_title="Olist 电商经营分析", page_icon="📦", layout="wide")


# --------------------------------------------------------------------------- 数据访问
@st.cache_data(ttl=3600, show_spinner=False)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    """每次查询新建只读连接，避免多会话共享连接导致的线程问题。"""
    con = duckdb.connect(str(DB_PATH), read_only=True)
    try:
        return con.execute(sql, params).fetchdf()
    finally:
        con.close()


def where_clause(start: date, end: date, states: list[str], alias: str = "o") -> tuple[str, list]:
    conds = [
        f"{alias}.order_status NOT IN ('canceled', 'unavailable')",
        f"{alias}.purchase_date BETWEEN ? AND ?",
    ]
    params: list = [start, end]
    if states:
        placeholders = ", ".join(["?"] * len(states))
        conds.append(f"{alias}.customer_state IN ({placeholders})")
        params.extend(states)
    return " AND ".join(conds), params


def style(fig: go.Figure, height: int = 340) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=8, r=8, t=24, b=8),
        font=dict(size=12),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


# --------------------------------------------------------------------------- 侧边栏
if not DB_PATH.exists():
    st.error("数仓尚未构建。请先运行：`python -m src.download && python -m src.build_warehouse && python -m src.run_metrics`")
    st.stop()

bounds = q(
    "SELECT MIN(purchase_date) AS min_d, MAX(purchase_date) AS max_d "
    "FROM fact_orders WHERE purchase_date IS NOT NULL"
).iloc[0]
min_d, max_d = bounds["min_d"], bounds["max_d"]

st.sidebar.header("筛选条件")
date_range = st.sidebar.date_input(
    "下单日期",
    value=(date(2017, 1, 1), date(2018, 8, 31)),
    min_value=min_d,
    max_value=max_d,
    help="数据集 2016 年与 2018 年 9 月样本极少，默认已剔除。",
)
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start_d, end_d = date_range
else:
    start_d, end_d = date(2017, 1, 1), date(2018, 8, 31)

state_options = q(
    "SELECT DISTINCT customer_state FROM fact_orders "
    "WHERE customer_state IS NOT NULL ORDER BY 1"
)["customer_state"].tolist()
states = st.sidebar.multiselect("客户所在州", state_options, placeholder="全部州")

st.sidebar.caption("数据：Olist 巴西电商公开数据集（9 张表 / 约 10 万订单）")

WHERE, PARAMS = where_clause(start_d, end_d, states)
P = tuple(PARAMS)

st.title("📦 Olist 电商经营分析")
st.caption(f"口径：剔除 canceled / unavailable 订单；时间 {start_d} ~ {end_d}；"
           f"州：{'全部' if not states else '、'.join(states)}")

# --------------------------------------------------------------------------- KPI
kpi = q(
    f"""
    SELECT
        COUNT(*) AS orders,
        SUM(COALESCE(payment_total, 0)) AS gmv,
        SUM(COALESCE(payment_total, 0)) / NULLIF(COUNT(*), 0) AS aov,
        AVG(review_score) AS score,
        COUNT(DISTINCT customer_unique_id) AS customers
    FROM fact_orders o
    WHERE {WHERE}
    """,
    P,
).iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("GMV（含运费）", f"R$ {kpi['gmv']:,.0f}")
c2.metric("订单量", f"{int(kpi['orders']):,}")
c3.metric("客单价", f"R$ {kpi['aov']:.2f}")
c4.metric("平均评分", f"{kpi['score']:.2f}" if pd.notna(kpi["score"]) else "—")

tab_overview, tab_user, tab_product, tab_ops = st.tabs(["总览", "用户", "商品", "履约"])

# --------------------------------------------------------------------------- 总览
with tab_overview:
    monthly = q(
        f"""
        SELECT o.purchase_month AS month,
               COUNT(*) AS orders,
               SUM(COALESCE(o.payment_total, 0)) AS gmv
        FROM fact_orders o
        WHERE {WHERE}
        GROUP BY 1 ORDER BY 1
        """,
        P,
    )
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=monthly["month"], y=monthly["gmv"], name="GMV",
               marker_color=BRAND, hovertemplate="R$ %{y:,.0f}<extra></extra>"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=monthly["month"], y=monthly["orders"], name="订单量",
                   mode="lines+markers", line=dict(color=ACCENT, width=2),
                   hovertemplate="%{y:,.0f} 单<extra></extra>"),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="GMV (R$)", secondary_y=False)
    fig.update_yaxes(title_text="订单量", secondary_y=True, showgrid=False)
    st.subheader("月度 GMV 与订单量")
    st.plotly_chart(style(fig, 360), width="stretch")

    left, right = st.columns([3, 2])
    with left:
        pay = q(
            f"""
            SELECT COALESCE(main_payment_type, 'unknown') AS payment_type,
                   COUNT(*) AS orders,
                   SUM(COALESCE(payment_total, 0)) AS gmv
            FROM fact_orders o
            WHERE {WHERE} AND payment_total IS NOT NULL
            GROUP BY 1 ORDER BY orders DESC
            """,
            P,
        )
        pay_fig = go.Figure(
            go.Pie(labels=pay["payment_type"], values=pay["orders"], hole=0.55,
                   marker=dict(colors=[BRAND, BRAND_LIGHT, ACCENT, "#C9CBD4", "#E4E5EA"]),
                   textinfo="label+percent", sort=False)
        )
        pay_fig.update_layout(template="plotly_white", height=340, margin=dict(l=8, r=8, t=24, b=8),
                              showlegend=False)
        st.subheader("支付方式占比")
        st.plotly_chart(pay_fig, width="stretch")

    with right:
        inst = q(
            f"""
            SELECT CASE
                       WHEN max_installments <= 1 THEN '1 期'
                       WHEN max_installments <= 3 THEN '2-3 期'
                       WHEN max_installments <= 6 THEN '4-6 期'
                       ELSE '7 期以上'
                   END AS bucket,
                   CASE
                       WHEN max_installments <= 1 THEN 1
                       WHEN max_installments <= 3 THEN 2
                       WHEN max_installments <= 6 THEN 3
                       ELSE 4
                   END AS ord,
                   COUNT(*) AS orders,
                   AVG(payment_total) AS aov
            FROM fact_orders o
            WHERE {WHERE} AND payment_total IS NOT NULL AND max_installments IS NOT NULL
            GROUP BY 1, 2 ORDER BY 2
            """,
            P,
        )
        inst_fig = go.Figure(
            go.Bar(x=inst["bucket"], y=inst["aov"], marker_color=BRAND,
                   text=[f"R$ {v:,.0f}" for v in inst["aov"]], textposition="outside",
                   hovertemplate="%{x}<br>客单价 R$ %{y:,.0f}<extra></extra>")
        )
        st.subheader("分期期数与客单价")
        st.plotly_chart(style(inst_fig, 340), width="stretch")
        if len(inst) >= 2:
            ratio = inst["aov"].iloc[-1] / inst["aov"].iloc[0]
            st.caption(f"7 期以上订单客单价是 1 期订单的 {ratio:.1f} 倍——分期是撬动高客单的工具，不是单纯的支付方式。")

# --------------------------------------------------------------------------- 用户
with tab_user:
    rfm = q(
        f"""
        WITH delivered AS (
            SELECT o.customer_unique_id, o.order_id, o.order_purchase_ts,
                   COALESCE(o.payment_total, 0) AS revenue
            FROM fact_orders o
            WHERE o.order_status = 'delivered'
              AND o.customer_unique_id IS NOT NULL
              AND o.order_purchase_ts IS NOT NULL
              AND {WHERE}
        ),
        ref AS (
            SELECT MAX(order_purchase_ts) AS ref_ts FROM fact_orders WHERE order_purchase_ts IS NOT NULL
        ),
        cl AS (
            SELECT customer_unique_id,
                   MAX(order_purchase_ts) AS last_ts,
                   COUNT(DISTINCT order_id) AS f,
                   SUM(revenue) AS m,
                   DATE_DIFF('day', MAX(order_purchase_ts), (SELECT ref_ts FROM ref)) AS r
            FROM delivered GROUP BY 1
        ),
        sc AS (
            SELECT *,
                   NTILE(5) OVER (ORDER BY r DESC) AS rs,
                   NTILE(5) OVER (ORDER BY f) AS fs,
                   NTILE(5) OVER (ORDER BY m) AS ms
            FROM cl
        )
        SELECT CASE
                   WHEN rs >= 4 AND ms >= 4 THEN '高价值活跃'
                   WHEN rs <= 2 AND ms >= 4 THEN '高价值沉睡'
                   WHEN rs >= 4 AND ms <= 2 THEN '潜力新客'
                   WHEN rs <= 2 AND ms <= 2 THEN '流失客户'
                   ELSE '一般客户'
               END AS segment,
               COUNT(*) AS customers,
               SUM(m) AS monetary,
               AVG(r) AS avg_recency_days,
               AVG(m) AS avg_monetary
        FROM sc GROUP BY 1
        """,
        P,
    )
    order = ["高价值活跃", "高价值沉睡", "潜力新客", "一般客户", "流失客户"]
    rfm["segment"] = pd.Categorical(rfm["segment"], categories=order, ordered=True)
    rfm = rfm.sort_values("segment")

    total_customers = int(rfm["customers"].sum())
    repeat_rate = q(
        f"""
        SELECT 1.0 * SUM(CASE WHEN c > 1 THEN 1 ELSE 0 END) / COUNT(*) AS rate
        FROM (
            SELECT customer_unique_id, COUNT(DISTINCT order_id) AS c
            FROM fact_orders o
            WHERE o.order_status = 'delivered' AND customer_unique_id IS NOT NULL AND {WHERE}
            GROUP BY 1
        )
        """,
        P,
    ).iloc[0]["rate"]

    m1, m2, m3 = st.columns(3)
    m1.metric("活跃客户数", f"{total_customers:,}")
    m2.metric("复购率", f"{repeat_rate:.1%}" if pd.notna(repeat_rate) else "—")
    m3.metric("最高分层客单贡献", f"R$ {rfm['avg_monetary'].max():,.0f}")

    left, right = st.columns([3, 2])
    with left:
        bar = go.Figure(
            go.Bar(
                x=rfm["segment"].astype(str), y=rfm["customers"],
                marker_color=[BRAND, BRAND_LIGHT, ACCENT, "#C9CBD4", "#E4E5EA"][: len(rfm)],
                text=[f"{v / total_customers:.0%}" for v in rfm["customers"]],
                textposition="outside",
                hovertemplate="%{x}<br>%{y:,} 人<extra></extra>",
            )
        )
        st.subheader("RFM 客户分层")
        st.plotly_chart(style(bar, 360), width="stretch")

    with right:
        st.subheader("各层平均消费")
        for _, row in rfm.iterrows():
            st.markdown(
                f"**{row['segment']}** ｜ {int(row['customers']):,} 人 ｜ "
                f"人均 R$ {row['avg_monetary']:,.0f} ｜ 平均 {row['avg_recency_days']:.0f} 天未下单"
            )

    st.info(
        "结论：本数据集 97% 的客户只下过 1 单，F 维度基本失效，分层主要由 R 与 M 决定。"
        "「高价值沉睡」是投入产出比最高的召回对象——历史消费高、但已长期未下单；"
        "「潜力新客」可用低门槛优惠券提升首单→二单转化。"
    )

# --------------------------------------------------------------------------- 商品
with tab_product:
    cat = q(
        f"""
        SELECT COALESCE(p.category_en, 'unknown') AS category,
               SUM(foi.price) AS revenue,
               COUNT(DISTINCT o.order_id) AS orders
        FROM fact_order_items foi
        JOIN fact_orders o ON o.order_id = foi.order_id
        LEFT JOIN dim_product p ON p.product_id = foi.product_id
        WHERE {WHERE}
        GROUP BY 1 ORDER BY revenue DESC
        """,
        P,
    )
    cat["share"] = cat["revenue"] / cat["revenue"].sum()
    cat["cum_share"] = cat["share"].cumsum()

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=cat["category"][:15], y=cat["revenue"][:15], name="营收",
               marker_color=BRAND, hovertemplate="R$ %{y:,.0f}<extra></extra>"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=cat["category"][:15], y=cat["cum_share"][:15], name="累计占比",
                   mode="lines+markers", line=dict(color=ACCENT, width=2),
                   hovertemplate="%{y:.0%}<extra></extra>"),
        secondary_y=True,
    )
    fig.update_yaxes(title_text="营收 (R$)", secondary_y=False)
    fig.update_yaxes(title_text="累计占比", secondary_y=True, tickformat=".0%", range=[0, 1])
    fig.update_xaxes(tickangle=-40)
    st.subheader("品类营收 Top 15 与帕累托曲线")
    st.plotly_chart(style(fig, 420), width="stretch")

    top5_share = cat["cum_share"].iloc[min(4, len(cat) - 1)]
    st.caption(f"前 5 个品类贡献 {top5_share:.0%} 的营收：集中度不高，长尾品类仍有经营价值。")

    st.subheader("品类明细")
    st.dataframe(
        cat.assign(
            占比=cat["share"].map("{:.1%}".format),
            累计=cat["cum_share"].map("{:.1%}".format),
        )[["category", "revenue", "orders", "占比", "累计"]]
        .rename(columns={"category": "品类", "revenue": "营收 (R$)", "orders": "订单数"})
        .style.format({"营收 (R$)": "{:,.0f}", "订单数": "{:,}"}),
        width="stretch",
        height=380,
    )

# --------------------------------------------------------------------------- 履约
with tab_ops:
    funnel = q(
        f"""
        WITH s AS (
            SELECT COUNT(*) AS placed,
                   SUM(CASE WHEN o.order_approved_ts    IS NOT NULL THEN 1 ELSE 0 END) AS approved,
                   SUM(CASE WHEN o.delivered_carrier_ts IS NOT NULL THEN 1 ELSE 0 END) AS shipped,
                   SUM(CASE WHEN o.delivered_customer_ts IS NOT NULL THEN 1 ELSE 0 END) AS delivered
            FROM fact_orders o WHERE {WHERE}
        ),
        rv AS (
            SELECT COUNT(*) AS n FROM fact_orders o
            WHERE {WHERE} AND o.delivered_customer_ts IS NOT NULL AND o.review_score IS NOT NULL
        )
        SELECT 1 AS step_order, '下单' AS step, placed AS orders FROM s
        UNION ALL SELECT 2, '支付通过', approved FROM s
        UNION ALL SELECT 3, '交给承运商', shipped FROM s
        UNION ALL SELECT 4, '送达客户', delivered FROM s
        UNION ALL SELECT 5, '收到评价', (SELECT n FROM rv)
        ORDER BY step_order
        """,
        P + P,
    )

    left, right = st.columns([2, 3])
    with left:
        ff = go.Figure(
            go.Funnel(
                y=funnel["step"], x=funnel["orders"],
                textinfo="value+percent initial",
                marker=dict(color=[BRAND, BRAND, BRAND_LIGHT, BRAND_LIGHT, "#C9CBD4"]),
                connector=dict(line=dict(color=GRID, width=1)),
            )
        )
        ff.update_layout(template="plotly_white", height=380, margin=dict(l=8, r=8, t=24, b=8))
        st.subheader("订单履约漏斗")
        st.plotly_chart(ff, width="stretch")

    with right:
        dv = q(
            f"""
            WITH b AS (
                SELECT CASE
                           WHEN o.delay_days < 0 THEN '提前送达'
                           WHEN o.delay_days = 0 THEN '准时'
                           WHEN o.delay_days BETWEEN 1 AND 3 THEN '延迟 1-3 天'
                           WHEN o.delay_days BETWEEN 4 AND 7 THEN '延迟 4-7 天'
                           WHEN o.delay_days BETWEEN 8 AND 15 THEN '延迟 8-15 天'
                           ELSE '延迟 15 天以上'
                       END AS bucket,
                       CASE
                           WHEN o.delay_days < 0 THEN 1
                           WHEN o.delay_days = 0 THEN 2
                           WHEN o.delay_days BETWEEN 1 AND 3 THEN 3
                           WHEN o.delay_days BETWEEN 4 AND 7 THEN 4
                           WHEN o.delay_days BETWEEN 8 AND 15 THEN 5
                           ELSE 6
                       END AS ord,
                       o.review_score
                FROM fact_orders o
                WHERE {WHERE} AND o.order_status = 'delivered'
                  AND o.delivered_customer_ts IS NOT NULL AND o.review_score IS NOT NULL
            )
            SELECT bucket, ord, COUNT(*) AS orders, AVG(review_score) AS score,
                   AVG(CASE WHEN review_score <= 2 THEN 1.0 ELSE 0.0 END) AS bad_rate
            FROM b GROUP BY 1, 2 ORDER BY 2
            """,
            P,
        )
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(x=dv["bucket"], y=dv["score"], name="平均评分",
                   marker_color=BRAND, hovertemplate="%{y:.2f} 分<extra></extra>"),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(x=dv["bucket"], y=dv["bad_rate"], name="差评率(≤2分)",
                       mode="lines+markers", line=dict(color=ACCENT, width=2),
                       hovertemplate="%{y:.1%}<extra></extra>"),
            secondary_y=True,
        )
        fig.update_yaxes(title_text="平均评分", range=[0, 5], secondary_y=False)
        fig.update_yaxes(title_text="差评率", tickformat=".0%", range=[0, 1],
                         showgrid=False, secondary_y=True)
        st.subheader("配送延迟与用户评分")
        st.plotly_chart(style(fig, 380), width="stretch")

    if not dv.empty:
        on_time = dv.loc[dv["bucket"] == "准时", "bad_rate"]
        worst = dv.loc[dv["bad_rate"].idxmax()]
        base = float(on_time.iloc[0]) if not on_time.empty else float(dv["bad_rate"].iloc[0])
        st.warning(
            f"关键发现：{worst['bucket']}的订单差评率 {worst['bad_rate']:.0%}，"
            f"是准时订单（{base:.0%}）的 {worst['bad_rate'] / base:.1f} 倍，"
            f"平均评分仅 {worst['score']:.2f}。履约时效是评分的第一驱动因素，"
            f"比商品质量、价格更可控——建议对高延迟品类单独设时效 SLA。"
        )

st.divider()
st.caption(
    "数据来源：Olist Brazilian E-Commerce Public Dataset（Kaggle，公开数据）。"
    "指标口径见 docs/metric_definitions.md；口径变化会直接改变结论，阅读时请以文档为准。"
)
