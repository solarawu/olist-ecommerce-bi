"""构建 DuckDB 数仓：staging -> 维度表 / 事实表。

用法：
    python -m src.build_warehouse
"""

from __future__ import annotations

import sys

from src.config import DB_PATH, OLIST_DIR, SQL_DIR, get_connection, render_sql

SQL_FILES = ["00_staging.sql", "01_dims.sql", "02_facts.sql"]


def build() -> None:
    if not (OLIST_DIR / "olist_orders_dataset.csv").exists():
        sys.exit("原始数据不存在，请先执行：python -m src.download")

    con = get_connection()
    try:
        for name in SQL_FILES:
            path = SQL_DIR / name
            print(f"执行 {name} ...", end=" ")
            con.execute(render_sql(path.read_text(encoding="utf-8")))
            print("OK")

        print("\n数仓构建完成，各表行数：")
        tables = con.execute(
            """
            SELECT table_schema, table_name
            FROM information_schema.tables
            WHERE table_schema IN ('staging', 'main')
            ORDER BY table_schema, table_name
            """
        ).fetchall()
        for schema, table in tables:
            count = con.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"').fetchone()[0]
            print(f"  {schema}.{table:<24} {count:>10,}")
    finally:
        con.close()

    print(f"\n数据库文件：{DB_PATH}")


if __name__ == "__main__":
    build()
