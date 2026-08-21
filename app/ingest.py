from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from app.config import LOG_DIR, get_settings
from app.library_client import ShanghaiLibraryClient
from app.sample_data import SAMPLE_RECORDS
from app.official_snapshot import load_snapshot
from app.storage import count_records, delete_demo_seed_records, delete_official_snapshot_records, upsert_records


DEFAULT_TERMS = [
    "盛宣怀",
    "鲁迅",
    "张骞",
    "张爱玲",
    "宋庆龄",
    "外滩",
    "南京路",
    "石库门",
    "里弄",
    "杨树浦",
    "提篮桥",
    "旧地址",
    "上海历史建筑",
    "上海历史事件",
    "近代报刊",
    "档案",
    "古籍",
    "家谱",
    "老照片",
    "老地图",
    "电影",
    "影院",
    "女性职业教育",
    "有轨电车",
    "公共汽车",
    "图书馆阅览室",
    "公园",
    "医院",
    "慈善",
    "展览会",
    "工会",
    "船票",
    "铁路时刻表",
    "百货公司广告",
    "学校年刊",
    "照相馆",
    "电话簿",
    "商号名录",
    "剧院",
    "庙会",
    "口述史",
    "门牌变更",
    "月份牌",
    "书店",
    "报刊广告",
    "城市治理",
    "渡口",
    "墓园",
    "方言地名",
    "货币",
    "银",
    "纸币",
    "海关",
    "口岸",
    "商路",
    "丝绸之路",
    "外交",
    "银行",
    "汇票",
    "票号",
    "航运",
]


def ingest(use_live: bool = False, terms: list[str] | None = None, limit_per_term: int = 6, seed_if_empty: bool = True) -> dict:
    settings = get_settings()
    terms = terms or DEFAULT_TERMS
    live_records = []
    errors = []
    if use_live:
        if not settings.api_key:
            errors.append("SHLIB_API_KEY is not set; skipped live API ingestion.")
        else:
            client = ShanghaiLibraryClient(settings.api_key)
            try:
                live_records = client.search_terms(terms, limit_per_term=limit_per_term)
            except Exception as exc:
                errors.append(f"Live API ingestion failed: {type(exc).__name__}: {exc}")
    snapshot_records = load_snapshot()
    replaced_snapshot = delete_official_snapshot_records() if snapshot_records else 0
    inserted_snapshot = upsert_records(snapshot_records)
    inserted_live = upsert_records(live_records)
    removed_seed = delete_demo_seed_records() if snapshot_records else 0
    inserted_seed = 0
    if seed_if_empty and count_records() == 0:
        inserted_seed = upsert_records(SAMPLE_RECORDS)
    elif seed_if_empty and not live_records and not snapshot_records:
        inserted_seed = upsert_records(SAMPLE_RECORDS)
    report = {
        "timestamp": datetime.now(UTC).isoformat(),
        "use_live": use_live,
        "terms": terms,
        "inserted_live": inserted_live,
        "inserted_official_snapshot": inserted_snapshot,
        "replaced_official_snapshot": replaced_snapshot,
        "removed_demo_seed": removed_seed,
        "inserted_seed": inserted_seed,
        "total_records": count_records(),
        "errors": errors,
    }
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    (LOG_DIR / "last_ingest_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Shanghai Library data or seed demo records.")
    parser.add_argument("--live", action="store_true", help="Try live Shanghai Library API ingestion.")
    parser.add_argument("--no-seed", action="store_true", help="Do not load seed records if live API fails.")
    parser.add_argument("--limit-per-term", type=int, default=6)
    parser.add_argument("--terms", nargs="*", default=DEFAULT_TERMS)
    args = parser.parse_args()
    report = ingest(
        use_live=args.live,
        terms=args.terms,
        limit_per_term=args.limit_per_term,
        seed_if_empty=not args.no_seed,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
