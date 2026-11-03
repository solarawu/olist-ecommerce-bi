# Contributor Guide

感谢你对这个项目感兴趣！以下是贡献前需要了解的内容。

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/your-username/olist-ecommerce-bi.git
cd olist-ecommerce-bi

# 安装依赖
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 跑完整流程（一次性从原始数据到看板）
python -m src.download
python -m src.build_warehouse
python -m src.run_metrics
python -m src.quality_check

# 启动看板
streamlit run dashboard/app.py
```

## 项目约定

- **数仓分层**：`staging`（原始）→ `dim_*`/`fact_*`（维度事实）→ `metrics.*`（指标）。新增分析请优先写 `sql/metrics/` 下的 SQL 文件，而非在 dashboard 里硬编码。
- **指标口径**：新增指标必须在 `docs/metric_definitions.md` 中同步定义，否则视为未完成。
- **数据质量**：新增 SQL 后请跑 `python -m src.quality_check` 确认没有破坏现有校验。
- **类型安全**：Python 代码使用 type hints，SQL 使用显式 `CAST` / `TRY_CAST`。

## 提 PR 前 Checklist

- [ ] 本地跑过 `python -m src.build_warehouse && python -m src.run_metrics`
- [ ] 看板能正常启动且无 traceback
- [ ] 新增指标已在 `docs/metric_definitions.md` 中定义
- [ ] 代码无 `ruff` / `pylint` 告警（可选，但建议）

## 常见扩展方向

- 卖家维度分析（GMV / 单量 / 发货时效排名）
- 州级地理对比分析
- 季节性 / 节假日效应
- 用户留存 Cohort 分析
- 同比 / 环比计算（需补月份对齐逻辑）
