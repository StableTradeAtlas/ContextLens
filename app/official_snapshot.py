from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import PROCESSED_DIR, RAW_DIR
from app.library_client import normalize_payload
from app.models import EvidenceRecord


SNAPSHOT_PATH = PROCESSED_DIR / "shlibrary_official_snapshot.json"
ROUTE_ALIASES = {
    "roads-place-names": "roads_place_names",
    "historic-architectures": "historic_architectures",
    "historical-events": "event_knowledge",
    "event-knowledge": "event_knowledge",
    "person-authority": "person_authority",
    "shanghai-almanac-organizations": "shanghai_yearbook_org",
    "shanghai-yearbook-org": "shanghai_yearbook_org",
    "place-names-culture": "place_names_culture",
    "ancient-book-engravers": "ancient_book_engravers",
    "data-keyword": "data_keyword",
}


def _source_identity(path: Path) -> tuple[str, str] | None:
    stem = path.stem
    if stem.startswith("api-cache-") or "-error-" in stem:
        return None
    for suffix, route in sorted(ROUTE_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        marker = f"-{suffix}-"
        if marker in stem:
            return stem.split(marker, 1)[0], route
    return None


def _load_payload(path: Path) -> Any | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict) and payload.get("error"):
        return None
    return payload


def build_snapshot(raw_dir: Path = RAW_DIR, output_path: Path = SNAPSHOT_PATH) -> dict[str, Any]:
    records: dict[str, EvidenceRecord] = {}
    source_files = 0
    generated_at = datetime.now(UTC).isoformat()
    for path in sorted(raw_dir.glob("*.json")):
        identity = _source_identity(path)
        if not identity:
            continue
        payload = _load_payload(path)
        if payload is None:
            continue
        term, route = identity
        payload_sha256 = hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        retrieved_at = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat()
        normalized = normalize_payload(payload, term=term, route_name=route)
        for record in normalized:
            if not record.source_uri.startswith("https://data.library.sh.cn/"):
                continue
            record.source = f"Shanghai Library official data snapshot ({route})"
            # A verified cache is official evidence, but it is not a live API call.
            # Keep the distinction explicit throughout health checks and the UI.
            record.is_live_api = False
            record.provenance_note = (
                "Official Shanghai Library API response preserved as a redacted, reproducible submission snapshot."
            )
            record.verification_notes = list(dict.fromkeys(record.verification_notes + [
                "Official URI retained; API key and request credentials are not stored.",
                "Snapshot payload hash is available in the lineage record.",
            ]))
            record.lineage = {
                "provider": "Shanghai Library",
                "dataset": route,
                "query_term": term,
                "retrieved_at": retrieved_at,
                "official_uri": record.source_uri,
                "payload_sha256": payload_sha256,
                "normalization": "ContextLens normalize_payload v1",
                "evidence_id": record.record_id,
                "source_mode": "verified_official_snapshot",
            }
            records[record.source_uri or record.record_id] = record
        source_files += 1
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "provider": "Shanghai Library",
        "source_file_count": source_files,
        "record_count": len(records),
        "records": [record.to_dict() for record in records.values()],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_snapshot(path: Path = SNAPSHOT_PATH) -> list[EvidenceRecord]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    records: list[EvidenceRecord] = []
    for item in payload.get("records", []):
        if not isinstance(item, dict):
            continue
        allowed = EvidenceRecord.__dataclass_fields__.keys()
        records.append(EvidenceRecord(**{key: value for key, value in item.items() if key in allowed}))
    return records


if __name__ == "__main__":
    snapshot = build_snapshot()
    print(f"Built Shanghai Library snapshot: {snapshot['record_count']} records from {snapshot['source_file_count']} responses")
