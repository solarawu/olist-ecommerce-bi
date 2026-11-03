"""执行指标层 SQL，把分析结果物化成 metrics schema 下的表。

用法：
    python -m src.run_metrics
"""

from __future__ import annotations

from src.config import METRICS_SQL_DIR, get_connection, render_sql


def run() -> None:
    con = get_connection()
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS metrics")
        for path in sorted(METRICS_SQL_DIR.glob("*.sql")):
            print(f"执行 {path.name} ...", end=" ")
            con.execute(render_sql(path.read_text(encoding="utf-8")))
            print("OK")

        print("\n指标表预览：")
        for (table,) in con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'metrics' ORDER BY table_name"
        ).fetchall():
            count = con.execute(f"SELECT COUNT(*) FROM metrics.{table}").fetchone()[0]
            print(f"  metrics.{table:<24} {count:>6,} 行")
    finally:
        con.close()


if __name__ == "__main__":
    run()
