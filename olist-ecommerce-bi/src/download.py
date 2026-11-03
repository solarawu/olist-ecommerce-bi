"""下载并解压 Olist 巴西电商公开数据集。

数据源：Kaggle - Brazilian E-Commerce Public Dataset by Olist
（公开数据集，无需登录即可通过 API 端点获取）

用法：
    python -m src.download
"""

from __future__ import annotations

import shutil
import sys
import urllib.request
import zipfile

from src.config import OLIST_DIR, RAW_DIR

DATASET_URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
ZIP_PATH = RAW_DIR / "olist.zip"

EXPECTED_FILES = [
    "olist_orders_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "product_category_name_translation.csv",
]


def _progress(block_num: int, block_size: int, total_size: int) -> None:
    if total_size <= 0:
        return
    downloaded = block_num * block_size
    percent = min(downloaded / total_size * 100, 100)
    sys.stdout.write(f"\r下载中 {percent:5.1f}%  ({downloaded / 1e6:.1f} / {total_size / 1e6:.1f} MB)")
    sys.stdout.flush()


def download() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 1_000_000:
        print(f"压缩包已存在，跳过下载：{ZIP_PATH}")
    else:
        print(f"开始下载：{DATASET_URL}")
        urllib.request.urlretrieve(DATASET_URL, ZIP_PATH, reporthook=_progress)
        print()

    with zipfile.ZipFile(ZIP_PATH) as zf:
        zf.extractall(OLIST_DIR)

    missing = [f for f in EXPECTED_FILES if not (OLIST_DIR / f).exists()]
    if missing:
        raise RuntimeError(f"解压后缺少文件：{missing}")

    shutil.rmtree(OLIST_DIR / "__MACOSX", ignore_errors=True)
    print(f"数据就绪：{OLIST_DIR}")
    for name in EXPECTED_FILES:
        size = (OLIST_DIR / name).stat().st_size / 1e6
        print(f"  {name:<48} {size:6.1f} MB")


if __name__ == "__main__":
    download()
