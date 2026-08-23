#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


QUERIES = [
    {"id": "zh01", "language": "zh", "query": "法租界道路更名与都市文化", "expected": ["xiafei"]},
    {"id": "zh02", "language": "zh", "query": "上海犹太难民与会堂", "expected": ["changyang"]},
    {"id": "zh03", "language": "zh", "query": "虹口文学文化街区", "expected": ["duolun"]},
    {"id": "zh04", "language": "zh", "query": "外滩金融建筑与滨江天际线", "expected": ["bund"]},
    {"id": "zh05", "language": "zh", "query": "静安商业旅馆与公共文化", "expected": ["nanjingwest"]},
    {"id": "zh06", "language": "zh", "query": "贝当路国际礼拜堂和公寓生活", "expected": ["hengshan"]},
    {"id": "zh07", "language": "zh", "query": "里弄与集合住宅的发展", "expected": ["chongqing"]},
    {"id": "zh08", "language": "zh", "query": "花园住宅与亚尔培坊", "expected": ["shaanxi"]},
    {"id": "zh09", "language": "zh", "query": "四川北路商业与革命活动", "expected": ["sichuan"]},
    {"id": "zh10", "language": "zh", "query": "霞飞路出版书局和美术展览", "expected": ["xiafei"]},
    {"id": "en01", "language": "en", "query": "Jewish refugees and a synagogue on Ward Road", "expected": ["changyang"]},
    {"id": "en02", "language": "en", "query": "literary culture and revolutionary sites in Hongkou", "expected": ["duolun"]},
    {"id": "en03", "language": "en", "query": "riverfront finance architecture and Shanghai skyline", "expected": ["bund"]},
    {"id": "en04", "language": "en", "query": "Bubbling Well Road commerce hotels and civic culture", "expected": ["nanjingwest"]},
    {"id": "en05", "language": "en", "query": "Avenue Petain apartments church and public life", "expected": ["hengshan"]},
    {"id": "en06", "language": "en", "query": "lane housing and modern apartment development", "expected": ["chongqing"]},
    {"id": "en07", "language": "en", "query": "garden residences and King Albert Lane", "expected": ["shaanxi"]},
    {"id": "en08", "language": "en", "query": "commercial street worker housing and revolutionary history", "expected": ["sichuan"]},
    {"id": "en09", "language": "en", "query": "Avenue Joffre publishing art and metropolitan culture", "expected": ["xiafei"]},
    {"id": "en10", "language": "en", "query": "Cathay Hotel signal tower and Huangpu River", "expected": ["bund"]},
    {"id": "cross01", "language": "zh-en", "query": "提篮桥 Jewish refuge history", "expected": ["changyang"]},
    {"id": "cross02", "language": "zh-en", "query": "窦乐安路 literary district", "expected": ["duolun"]},
    {"id": "cross03", "language": "zh-en", "query": "外滩 waterfront infrastructure", "expected": ["bund"]},
    {"id": "cross04", "language": "zh-en", "query": "静安寺路 Bubbling Well Road", "expected": ["nanjingwest"]},
    {"id": "cross05", "language": "zh-en", "query": "贝当路 Avenue Petain", "expected": ["hengshan"]},
    {"id": "cross06", "language": "zh-en", "query": "灵宝路 lane housing", "expected": ["chongqing"]},
    {"id": "cross07", "language": "zh-en", "query": "亚尔培坊 garden residences", "expected": ["shaanxi"]},
    {"id": "cross08", "language": "zh-en", "query": "北四川路 commercial culture", "expected": ["sichuan"]},
    {"id": "cross09", "language": "zh-en", "query": "霞飞路 Avenue Joffre", "expected": ["xiafei"]},
    {"id": "cross10", "language": "zh-en", "query": "华德路 Ward Road prison synagogue", "expected": ["changyang"]},
]


def compact(value: object) -> str:
    if isinstance(value, list):
        return "；".join(compact(item) for item in value if compact(item))
    if isinstance(value, dict):
        return "；".join(f"{key}: {compact(item)}" for key, item in value.items() if compact(item))
    return str(value or "").strip()


def main() -> None:
    import sys
    sys.path.insert(0, str(ROOT))
    from app.catalog import CATALOG

    snapshot = json.loads((ROOT / "data/processed/shlibrary_official_snapshot.json").read_text())
    records = snapshot["records"]
    documents = []
    for street in CATALOG:
        names = {street["address"], street["name_zh"], street["name_en"]}
        names.update(part.strip() for part in street["name_zh"].replace("·", "/").split("/") if part.strip())
        searchable = []
        matched_ids = []
        for record in records:
            haystack = compact({
                "title": record.get("title"), "snippet": record.get("snippet"),
                "places": record.get("places"), "topics": record.get("topics"), "raw": record.get("raw"),
            })
            if any(name and name in haystack for name in names):
                searchable.append(f"{record.get('title', '')}。{record.get('snippet', '')}")
                matched_ids.append(record["record_id"])
        text = "\n".join([
            f"街道 / Street: {street['name_zh']} / {street['name_en']}",
            f"区域 / District: {street['district_zh']} / {street['district_en']}",
            f"年代 / Coverage: {street['period_zh']} / {street['period_en']}",
            f"中文简介: {street['intro_zh']}", f"English overview: {street['intro_en']}",
            f"主题 / Themes: {'；'.join(street['themes_zh'])} / {'; '.join(street['themes_en'])}",
            *searchable,
        ])
        documents.append({
            "street_id": street["id"], "name_zh": street["name_zh"], "name_en": street["name_en"],
            "themes_zh": street["themes_zh"], "themes_en": street["themes_en"],
            "matched_record_ids": matched_ids, "matched_record_count": len(matched_ids), "text": text,
            "text_sha256": hashlib.sha256(text.encode()).hexdigest(),
        })
    payload = {
        "schema_version": "1.0", "source_snapshot_sha256": hashlib.sha256(
            (ROOT / "data/processed/shlibrary_official_snapshot.json").read_bytes()
        ).hexdigest(), "document_count": len(documents), "query_count": len(QUERIES),
        "documents": documents, "evaluation_queries": QUERIES,
    }
    output = ROOT / "data/processed/gpu_corpus_manifest.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"Prepared {len(documents)} street documents and {len(QUERIES)} evaluation queries: {output}")


if __name__ == "__main__":
    main()
