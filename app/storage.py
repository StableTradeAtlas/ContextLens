from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.config import DB_PATH, LOG_DIR, ensure_dirs
from app.models import EvidenceRecord


SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
  record_id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  snippet TEXT NOT NULL,
  source TEXT NOT NULL,
  source_uri TEXT NOT NULL,
  dataset TEXT NOT NULL,
  date TEXT,
  persons TEXT NOT NULL,
  places TEXT NOT NULL,
  topics TEXT NOT NULL,
  evidence_type TEXT NOT NULL DEFAULT 'source_record',
  provenance_note TEXT NOT NULL DEFAULT '',
  time_span TEXT NOT NULL DEFAULT '',
  geo_json TEXT NOT NULL DEFAULT '{}',
  public_tags TEXT NOT NULL DEFAULT '[]',
  verification_notes TEXT NOT NULL DEFAULT '[]',
  lineage_json TEXT NOT NULL DEFAULT '{}',
  raw_json TEXT NOT NULL,
  is_live_api INTEGER NOT NULL DEFAULT 0
);
"""

MIGRATION_COLUMNS = {
    "evidence_type": "TEXT NOT NULL DEFAULT 'source_record'",
    "provenance_note": "TEXT NOT NULL DEFAULT ''",
    "time_span": "TEXT NOT NULL DEFAULT ''",
    "geo_json": "TEXT NOT NULL DEFAULT '{}'",
    "public_tags": "TEXT NOT NULL DEFAULT '[]'",
    "verification_notes": "TEXT NOT NULL DEFAULT '[]'",
    "lineage_json": "TEXT NOT NULL DEFAULT '{}'",
}


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    ensure_dirs()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute(SCHEMA)
    ensure_schema_columns(conn)
    return conn


def ensure_schema_columns(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(records)").fetchall()}
    for column, ddl in MIGRATION_COLUMNS.items():
        if column not in existing:
            conn.execute(f"ALTER TABLE records ADD COLUMN {column} {ddl}")
    conn.commit()


def upsert_records(records: list[EvidenceRecord], db_path: Path = DB_PATH) -> int:
    if not records:
        return 0
    with connect(db_path) as conn:
        for r in records:
            conn.execute(
                """
                INSERT OR REPLACE INTO records
                (
                  record_id, title, snippet, source, source_uri, dataset, date, persons, places, topics,
                  evidence_type, provenance_note, time_span, geo_json, public_tags, verification_notes,
                  lineage_json, raw_json, is_live_api
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r.record_id,
                    r.title,
                    r.snippet,
                    r.source,
                    r.source_uri,
                    r.dataset,
                    r.date,
                    json.dumps(r.persons, ensure_ascii=False),
                    json.dumps(r.places, ensure_ascii=False),
                    json.dumps(r.topics, ensure_ascii=False),
                    r.evidence_type,
                    r.provenance_note,
                    r.time_span,
                    json.dumps(r.geo, ensure_ascii=False),
                    json.dumps(r.public_tags, ensure_ascii=False),
                    json.dumps(r.verification_notes, ensure_ascii=False),
                    json.dumps(r.lineage, ensure_ascii=False),
                    json.dumps(r.raw, ensure_ascii=False),
                    1 if r.is_live_api else 0,
                ),
            )
        conn.commit()
    return len(records)


def load_records(db_path: Path = DB_PATH) -> list[EvidenceRecord]:
    with connect(db_path) as conn:
        rows = conn.execute("SELECT * FROM records ORDER BY is_live_api DESC, record_id").fetchall()
    return [row_to_record(row) for row in rows]


def get_record(record_id: str, db_path: Path = DB_PATH) -> EvidenceRecord | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM records WHERE record_id = ?", (record_id,)).fetchone()
    return row_to_record(row) if row else None


def count_records(db_path: Path = DB_PATH) -> int:
    with connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM records").fetchone()
    return int(row["n"])


def count_records_by_source(db_path: Path = DB_PATH) -> dict[str, int]:
    with connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT
              COUNT(*) AS total,
              COALESCE(SUM(CASE WHEN is_live_api = 1 THEN 1 ELSE 0 END), 0) AS live,
              COALESCE(SUM(CASE WHEN lineage_json LIKE '%verified_official_snapshot%' THEN 1 ELSE 0 END), 0) AS official_snapshot,
              COALESCE(SUM(CASE WHEN evidence_type LIKE '%seed%' OR raw_json LIKE '%\"demo_seed\": true%' THEN 1 ELSE 0 END), 0) AS seed
            FROM records
            """
        ).fetchone()
    return {
        "records": int(row["total"]),
        "live_records": int(row["live"]),
        "official_snapshot_records": int(row["official_snapshot"]),
        "seed_records": int(row["seed"]),
    }


def delete_demo_seed_records(db_path: Path = DB_PATH) -> int:
    """Remove transparent prototype seeds once an official snapshot is available."""
    with connect(db_path) as conn:
        cursor = conn.execute(
            "DELETE FROM records WHERE evidence_type LIKE '%seed%' OR raw_json LIKE '%\"demo_seed\": true%'"
        )
        conn.commit()
        return max(0, int(cursor.rowcount or 0))


def delete_official_snapshot_records(db_path: Path = DB_PATH) -> int:
    """Replace the packaged snapshot atomically without deleting newer live records."""
    with connect(db_path) as conn:
        cursor = conn.execute("DELETE FROM records WHERE lineage_json LIKE '%verified_official_snapshot%'")
        conn.commit()
        return max(0, int(cursor.rowcount or 0))


def load_last_ingest_report() -> dict:
    path = LOG_DIR / "last_ingest_report.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"error": "last_ingest_report.json is not valid JSON"}


def row_to_record(row: sqlite3.Row) -> EvidenceRecord:
    keys = set(row.keys())

    def value(key: str, default: str = "") -> str:
        return row[key] if key in keys and row[key] is not None else default

    return EvidenceRecord(
        record_id=row["record_id"],
        title=row["title"],
        snippet=row["snippet"],
        source=row["source"],
        source_uri=row["source_uri"],
        dataset=row["dataset"],
        date=row["date"] or "",
        persons=json.loads(row["persons"] or "[]"),
        places=json.loads(row["places"] or "[]"),
        topics=json.loads(row["topics"] or "[]"),
        raw=json.loads(row["raw_json"] or "{}"),
        is_live_api=bool(row["is_live_api"]),
        evidence_type=value("evidence_type", "source_record"),
        provenance_note=value("provenance_note", ""),
        time_span=value("time_span", ""),
        geo=json.loads(value("geo_json", "{}") or "{}"),
        public_tags=json.loads(value("public_tags", "[]") or "[]"),
        verification_notes=json.loads(value("verification_notes", "[]") or "[]"),
        lineage=json.loads(value("lineage_json", "{}") or "{}"),
    )
