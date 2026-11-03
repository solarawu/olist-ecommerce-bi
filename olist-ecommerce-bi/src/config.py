"""项目路径与数据库连接的统一入口。"""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OLIST_DIR = RAW_DIR / "olist"
PROCESSED_DIR = DATA_DIR / "processed"
WAREHOUSE_DIR = DATA_DIR / "warehouse"
DB_PATH = WAREHOUSE_DIR / "olist.duckdb"

SQL_DIR = BASE_DIR / "sql"
METRICS_SQL_DIR = SQL_DIR / "metrics"


def get_connection(read_only: bool = False):
    """返回 DuckDB 连接，调用方负责关闭。"""
    import duckdb

    WAREHOUSE_DIR.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def render_sql(sql: str) -> str:
    """把 SQL 中的路径占位符替换成本机绝对路径。"""
    return sql.replace("{{OLIST_DIR}}", OLIST_DIR.as_posix())
