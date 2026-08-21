from __future__ import annotations

import hashlib
import json
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import RAW_DIR
from app.models import EvidenceRecord


class ShanghaiLibraryClient:
    """Small API client for Shanghai Library open-data experiments.

    The official documentation exposes API-keyed REST/JSON-LD access patterns.
    This v0.1 client tries a small set of conservative search routes and stores
    raw responses for traceability. If the local network blocks access, callers
    should fall back to demo seed data.
    """

    def __init__(self, api_key: str, timeout: int = 18, request_interval: float = 2.05, cache_ttl: int = 86_400) -> None:
        self.api_key = api_key
        self.timeout = timeout
        self.request_interval = request_interval
        self.cache_ttl = cache_ttl
        self._last_request_at = 0.0
        # urllib can silently pick up macOS/system proxy settings. In this local
        # environment that caused HTTPS CONNECT 403 errors even though curl worked.
        self.opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=verified_ssl_context()),
        )

    def search_term(self, term: str, limit: int = 10) -> list[EvidenceRecord]:
        routes = self._routes_for_term(term)
        records: list[EvidenceRecord] = []
        for route_name, url in routes:
            try:
                payload = self._get_json_or_text(url)
            except Exception as exc:
                self._write_error(term, route_name, exc)
                continue
            self._write_raw(term, route_name, payload)
            normalized = normalize_payload(payload, term=term, route_name=route_name)
            records.extend(normalized)
            if len(records) >= limit:
                break
        return records[:limit]

    def search_terms(self, terms: list[str], limit_per_term: int = 8) -> list[EvidenceRecord]:
        seen: set[str] = set()
        out: list[EvidenceRecord] = []
        for term in terms:
            for record in self.search_term(term, limit=limit_per_term):
                key = record.source_uri or record.record_id
                if key in seen:
                    continue
                seen.add(key)
                out.append(record)
        return out

    def search_roads(self, term: str, limit: int = 8) -> list[dict[str, Any]]:
        q = urllib.parse.quote(term)
        key = urllib.parse.quote(self.api_key)
        url = (
            "https://data1.library.sh.cn/shnh/wkl/webapi/road/list"
            f"?freetext={q}&type=2&pageth=1&pageSize={max(1, min(limit, 20))}&key={key}"
        )
        payload = self._get_json_or_text(url)
        self._write_raw(term, "roads_place_names", payload)
        return payload_items(payload)

    def search_architectures(self, term: str, limit: int = 8) -> list[dict[str, Any]]:
        q = urllib.parse.quote(term)
        key = urllib.parse.quote(self.api_key)
        url = (
            "https://data1.library.sh.cn/shnh/gmwx/webapi/architecture/getArchitectures"
            f"?freetext={q}&isRed=3&pageth=1&pageSize={max(1, min(limit, 20))}&key={key}"
        )
        payload = self._get_json_or_text(url)
        self._write_raw(term, "historic_architectures", payload)
        return payload_items(payload)

    def search_events(self, term: str, limit: int = 10) -> list[dict[str, Any]]:
        q = urllib.parse.quote(term)
        key = urllib.parse.quote(self.api_key)
        url = (
            "https://data1.library.sh.cn/webapi/hsly/route/getEventList"
            f"?eventFreeText={q}&pageth=1&pageSize={max(1, min(limit, 20))}&key={key}"
        )
        payload = self._get_json_or_text(url)
        self._write_raw(term, "historical_events", payload)
        return payload_items(payload)

    def fetch_event_detail(self, uri: str) -> dict[str, Any]:
        """Fetch relation lists (people, institutions and places) for an event."""
        key = urllib.parse.quote(self.api_key)
        value = urllib.parse.quote(uri, safe="")
        url = f"https://data1.library.sh.cn/webapi/hsly/route/getEventDetail?uri={value}&key={key}"
        payload = self._get_json_or_text(url)
        items = payload_items(payload)
        return items[0] if items else {}

    def fetch_architecture_detail(self, uri: str) -> dict[str, Any]:
        """Fetch the event/person/work relations omitted from building lists."""
        key = urllib.parse.quote(self.api_key)
        value = urllib.parse.quote(uri, safe="")
        url = (
            "https://data1.library.sh.cn/shnh/gmwx/webapi/architecture/getArchitectureDetail"
            f"?uri={value}&key={key}"
        )
        payload = self._get_json_or_text(url)
        items = payload_items(payload)
        if items:
            return items[0]
        data = payload.get("data") if isinstance(payload, dict) else None
        return data if isinstance(data, dict) else {}

    def search_people(self, name: str, limit: int = 4) -> list[dict[str, Any]]:
        """Search the Shanghai Library name-authority dataset by an explicit name."""
        q = urllib.parse.quote(name)
        key = urllib.parse.quote(self.api_key)
        url = (
            "https://data1.library.sh.cn/persons/data"
            f"?fname={q}&pageth=1&pageSize={max(1, min(limit, 10))}&key={key}"
        )
        payload = self._get_json_or_text(url)
        self._write_raw(name, "person_authority", payload)
        return payload_items(payload)

    def search_organizations(self, name: str, limit: int = 4) -> list[dict[str, Any]]:
        """Search the Shanghai Almanac institution directory by an explicit label."""
        q = urllib.parse.quote(name)
        key = urllib.parse.quote(self.api_key)
        url = (
            "https://data1.library.sh.cn/shnh/whzk/webapi/org/list"
            f"?freetext={q}&pageth=1&pageSize={max(1, min(limit, 10))}&key={key}"
        )
        payload = self._get_json_or_text(url)
        self._write_raw(name, "shanghai_almanac_organizations", payload)
        return payload_items(payload)

    def fetch_entity(self, uri: str) -> dict[str, Any]:
        value = canonical_source_uri(uri)
        if not value.startswith("https://data.library.sh.cn/entity/"):
            return {}
        key = urllib.parse.quote(self.api_key)
        separator = "&" if "?" in value else "?"
        payload = self._get_json_or_text(f"{value}{separator}key={key}")
        return payload if isinstance(payload, dict) else {}

    def _routes_for_term(self, term: str) -> list[tuple[str, str]]:
        q = urllib.parse.quote(term)
        key = urllib.parse.quote(self.api_key)
        return [
            ("data_keyword", f"https://data.library.sh.cn/data/{q}?key={key}"),
            ("shanghai_yearbook_org", f"https://data1.library.sh.cn/shnh/whzk/webapi/org/list?freetext={q}&pageth=1&pageSize=8&key={key}"),
            ("event_knowledge", f"https://data1.library.sh.cn/webapi/hsly/route/getEventList?eventFreeText={q}&pageth=1&pageSize=8&key={key}"),
            ("place_names_culture", f"https://data1.library.sh.cn/shnh/dmz/webapi/geonames/list?type=4&freetext={q}&pageth=1&pageSize=8&key={key}"),
            ("roads_place_names", f"https://data1.library.sh.cn/shnh/wkl/webapi/road/list?freetext={q}&type=2&pageth=1&pageSize=8&key={key}"),
            ("ancient_book_engravers", f"https://data1.library.sh.cn/webapi/kg/list?freetext={q}&pageNum=1&key={key}"),
        ]

    def _get_json_or_text(self, url: str) -> Any:
        cache_path = self._cache_path(url)
        cached = self._read_cache(cache_path)
        if cached is not None and time.time() - cache_path.stat().st_mtime <= self.cache_ttl:
            return cached
        self._throttle()
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/json, application/ld+json, text/plain, */*",
                "User-Agent": "ContextLensODCDemo/0.4",
            },
        )
        try:
            with self.opener.open(request, timeout=self.timeout) as response:
                body = response.read()
                text = body.decode("utf-8", errors="replace")
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = {"text": text, "content_type": response.headers.get("content-type", "")}
        except Exception:
            # An expired verified response is safer than fabricating data when
            # the official API is temporarily offline or rate-limited.
            if cached is not None:
                return cached
            raise
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def _cache_path(self, url: str) -> Path:
        redacted_url = re.sub(r"([?&]key=)[^&]*", r"\1REDACTED", url)
        digest = hashlib.sha256(redacted_url.encode("utf-8")).hexdigest()[:24]
        return RAW_DIR / f"api-cache-{digest}.json"

    @staticmethod
    def _read_cache(path: Path) -> Any | None:
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if self._last_request_at and elapsed < self.request_interval:
            time.sleep(self.request_interval - elapsed)
        self._last_request_at = time.monotonic()

    def _write_raw(self, term: str, route_name: str, payload: Any) -> None:
        slug = safe_slug(f"{term}-{route_name}")
        path = RAW_DIR / f"{slug}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_error(self, term: str, route_name: str, exc: Exception) -> None:
        slug = safe_slug(f"{term}-{route_name}-error")
        path = RAW_DIR / f"{slug}.json"
        path.write_text(
            json.dumps(
                {"term": term, "route": route_name, "error_type": type(exc).__name__, "error": str(exc)},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )


def normalize_payload(payload: Any, term: str, route_name: str) -> list[EvidenceRecord]:
    items = extract_items(payload)
    records: list[EvidenceRecord] = []
    for idx, item in enumerate(items):
        title = pick_first(
            item,
            [
                "title",
                "label",
                "name",
                "nameS",
                "nameT",
                "fname",
                "chsAgent",
                "chsTitle",
                "titleChs",
                "nameChs",
                "workTitle",
                "instanceTitle",
                "event_name",
                "题名",
                "名称",
            ],
        )
        uri = pick_first(item, ["uri", "@id", "id", "url", "link", "resource", "资源"])
        snippet = pick_first(
            item,
            [
                "description",
                "abstract",
                "summary",
                "note",
                "content",
                "text",
                "hasBody",
                "noteOfSource",
                "dateLabel",
                "简介",
                "摘要",
                "说明",
            ],
        )
        date = pick_first(item, ["date", "year", "dynasty", "created", "出版年", "朝代"])
        title, snippet = improve_title_snippet(term, route_name, item, title, snippet, uri)
        if not title and not snippet:
            text = json.dumps(item, ensure_ascii=False)
            title = f"{term} related record"
            snippet = text[:260]
        record_key = uri or f"{route_name}-{term}-{idx}-{json.dumps(item, ensure_ascii=False)[:80]}"
        digest = hashlib.sha1(record_key.encode("utf-8")).hexdigest()[:12]
        source_uri = canonical_source_uri(uri) or api_record_reference(route_name, term, digest)
        evidence_type = infer_evidence_type(route_name, item)
        persons = extract_metadata_values(item, ["person", "agent", "author", "creator", "chsAgent", "姓名", "人物", "责任者"])
        places = extract_metadata_values(item, ["place", "geo", "address", "road", "location", "地点", "地名", "地址", "道路"])
        topic_values = extract_metadata_values(item, ["subject", "keyword", "classification", "type", "roles", "主题", "分类", "类别"])
        time_span = clean_text(date or pick_first(item, ["begin", "end", "dateLabel", "年代", "起讫时间"]))
        records.append(
            EvidenceRecord(
                record_id=f"shlib-{digest}",
                title=clean_text(title or f"{term} related record"),
                snippet=clean_text(snippet or ""),
                source=f"Shanghai Library Open Data API ({route_name})",
                source_uri=source_uri,
                dataset=route_name,
                date=clean_text(date or ""),
                persons=persons,
                places=places,
                topics=unique_values([term, route_name, evidence_type] + topic_values),
                raw=item if isinstance(item, dict) else {"value": item},
                is_live_api=True,
                evidence_type=evidence_type,
                provenance_note=live_provenance_note(route_name),
                time_span=time_span,
                geo=infer_geo_stub(route_name, item, places),
                public_tags=infer_public_tags(term, route_name, item),
                verification_notes=live_verification_notes(route_name, source_uri),
                lineage={
                    "provider": "Shanghai Library",
                    "dataset": route_name,
                    "query_term": term,
                    "retrieved_at": datetime.now(UTC).isoformat(),
                    "official_uri": source_uri,
                    "normalization": "ContextLens normalize_payload v1",
                    "evidence_id": f"shlib-{digest}",
                    "source_mode": "live_api",
                },
            )
        )
    return records


def verified_ssl_context() -> ssl.SSLContext:
    """Return a verified TLS context, with certifi as a safe macOS fallback."""
    context = ssl.create_default_context()
    try:
        import certifi  # type: ignore

        context.load_verify_locations(cafile=certifi.where())
    except Exception:
        # A correctly configured system trust store remains fully verified.
        pass
    return context


def payload_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    for key in ("data", "resultList", "items", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def canonical_source_uri(uri: str) -> str:
    value = clean_text(uri or "")
    if not value:
        return ""
    if value.startswith("http://data.library.sh.cn/"):
        return "https://" + value.removeprefix("http://")
    return value


def improve_title_snippet(term: str, route_name: str, item: dict[str, Any], title: str, snippet: str, uri: str) -> tuple[str, str]:
    if route_name == "data_keyword":
        data = pick_first(item, ["data"])
        if data:
            title = title or f"{term}：权威数据实体"
            snippet = snippet or f"Authority/entity lookup result for “{term}”: {data}"
    if route_name == "shanghai_yearbook_org":
        title = title or pick_first(item, ["name"])
        source = pick_first(item, ["noteOfSource"])
        snippet = snippet or f"Shanghai Yearbook organization record. Source dataset: {source or 'unknown'}."
    if route_name == "event_knowledge":
        snippet = snippet or pick_first(item, ["description", "dateLabel", "begin", "end"])
    if route_name == "ancient_book_engravers":
        roles = pick_first(item, ["roles"])
        anno = item.get("annoList")
        titles = []
        if isinstance(anno, list):
            for entry in anno[:3]:
                if isinstance(entry, dict):
                    t = pick_first(entry, ["chsTitle", "title", "identifier", "classification"])
                    if t:
                        titles.append(t)
        snippet = snippet or f"Ancient-book related person/work record. Roles: {roles}. Related works: {'；'.join(titles)}."
    if uri and uri not in snippet:
        snippet = snippet or f"Source URI: {uri}"
    return title, snippet


def infer_evidence_type(route_name: str, item: dict[str, Any]) -> str:
    route_types = {
        "data_keyword": "authority_entity",
        "shanghai_yearbook_org": "organization_record",
        "event_knowledge": "event_record",
        "place_names_culture": "gazetteer_record",
        "roads_place_names": "road_place_record",
        "ancient_book_engravers": "bibliographic_or_rare_book_record",
    }
    value = route_types.get(route_name, "source_record")
    raw_text = json.dumps(item, ensure_ascii=False)[:1200]
    if any(term in raw_text for term in ["家谱", "谱牒", "族谱"]):
        return "genealogy_record"
    if any(term in raw_text for term in ["报", "刊", "期刊", "newspaper"]):
        return "periodical_record"
    if any(term in raw_text for term in ["照片", "图像", "地图", "image", "map"]):
        return "visual_or_map_record"
    return value


def live_provenance_note(route_name: str) -> str:
    notes = {
        "data_keyword": "Live Shanghai Library authority/entity lookup normalized by ContextLens.",
        "shanghai_yearbook_org": "Live Shanghai Library organization-style record; verify name and source field before final citation.",
        "event_knowledge": "Live Shanghai Library event route record; verify date labels and event scope before timeline use.",
        "place_names_culture": "Live Shanghai Library place-name record; verify historical-to-modern place mapping before map publication.",
        "roads_place_names": "Live Shanghai Library road/place-name record; verify road type and naming period.",
        "ancient_book_engravers": "Live Shanghai Library rare-book/knowledge-graph record; verify work title, role, and version.",
    }
    return notes.get(route_name, "Live Shanghai Library record normalized by ContextLens.")


def live_verification_notes(route_name: str, source_uri: str) -> list[str]:
    notes = ["Open the source detail and verify title, dataset, and date before public submission."]
    if route_name in {"place_names_culture", "roads_place_names"}:
        notes.append("Cross-check historical name variants against a gazetteer or map layer.")
    if route_name == "event_knowledge":
        notes.append("Do not turn an event label into causality unless another source supports the link.")
    if route_name == "ancient_book_engravers":
        notes.append("Check whether the record describes a person, a work, or a role relation.")
    if source_uri.startswith("shlib-api://"):
        notes.append("This is an API-route reference, so ContextLens exposes a local source page rather than the API key URL.")
    return notes


def infer_geo_stub(route_name: str, item: dict[str, Any], places: list[str]) -> dict[str, Any]:
    lat = pick_first(item, ["lat", "latitude", "纬度"])
    lon = pick_first(item, ["lon", "lng", "longitude", "经度"])
    if lat and lon:
        return {"lat": lat, "lon": lon, "status": "provided_by_source"}
    if route_name in {"place_names_culture", "roads_place_names"} or places:
        return {"status": "needs_geocoding", "place_candidates": places[:5]}
    return {}


def infer_public_tags(term: str, route_name: str, item: dict[str, Any]) -> list[str]:
    text = f"{term} {route_name} {json.dumps(item, ensure_ascii=False)[:1600]}"
    tags = []
    checks = [
        ("city_walk", ["外滩", "道路", "旧址", "地名", "建筑", "里弄", "place", "road"]),
        ("family_memory", ["家谱", "人名", "姓名", "祖籍", "族谱", "person"]),
        ("document_detective", ["文献", "档案", "古籍", "题名", "版本", "报刊", "rare"]),
        ("public_culture", ["鲁迅", "张爱玲", "宋庆龄", "出版", "电影", "书店", "文化"]),
        ("shanghai_world", ["盛宣怀", "海关", "口岸", "银行", "商人", "航运", "贸易"]),
    ]
    for tag, terms in checks:
        if any(token.lower() in text.lower() for token in terms):
            tags.append(tag)
    return tags or ["library_open_data"]


def extract_metadata_values(item: dict[str, Any], keys: list[str], limit: int = 6) -> list[str]:
    values = []
    for key in keys:
        text = pick_first(item, [key])
        if text:
            values.extend(split_metadata_value(text))
    for key, value in item.items():
        key_l = str(key).lower()
        if any(k.lower() in key_l for k in keys):
            values.extend(split_metadata_value(flatten_value(value)))
    return unique_values(values)[:limit]


def split_metadata_value(value: str) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    parts = re.split(r"[;,，；、|｜/]+", text)
    cleaned = []
    for part in parts:
        item = clean_text(part)
        if 2 <= len(item) <= 42 and not item.startswith(("{", "[")):
            cleaned.append(item)
    return cleaned


def unique_values(values: list[str]) -> list[str]:
    seen = set()
    output = []
    for value in values:
        cleaned = clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        output.append(cleaned)
    return output


def extract_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    if set(payload.keys()) == {"result"} and payload.get("result") in ({}, [], None, "", "-1", -1, "0", 0, False):
        return []
    data_obj = payload.get("data")
    if isinstance(data_obj, dict) and data_obj.get("result") == []:
        return []
    candidates = [
        payload.get("data"),
        payload.get("results"),
        payload.get("result"),
        payload.get("datas"),
        payload.get("items"),
        payload.get("instances"),
        payload.get("@graph"),
        payload.get("records"),
    ]
    for candidate in candidates:
        if isinstance(candidate, list):
            return [x for x in candidate if isinstance(x, dict)]
        if isinstance(candidate, dict):
            nested = extract_items(candidate)
            if nested:
                return nested
    if "text" in payload:
        text = str(payload.get("text", "")).strip()
        if text:
            return [{"title": "API text response", "description": text[:900], "uri": ""}]
    return [payload] if payload else []


def pick_first(item: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        if key in item and item[key] not in (None, "", []):
            return flatten_value(item[key])
    for key, value in item.items():
        key_l = str(key).lower()
        if any(k.lower() in key_l for k in keys) and value not in (None, "", []):
            return flatten_value(value)
    return ""


def flatten_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        flattened = [flatten_value(v) for v in value[:8]]
        preferred = [v for v in flattened if "@chs" in v or "@cht" in v]
        values = preferred or flattened
        return "；".join(v for v in values[:4] if v)
    if isinstance(value, dict):
        for key in ("label", "name", "value", "@value", "title", "uri", "@id"):
            if key in value:
                return flatten_value(value[key])
        return json.dumps(value, ensure_ascii=False)[:260]
    return str(value)


def clean_text(text: str) -> str:
    cleaned = str(text).replace("@chs", "").replace("@cht", "").replace("；；", "；")
    return " ".join(cleaned.replace("\r", " ").replace("\n", " ").split()).strip("；,， ")


def api_record_reference(route_name: str, term: str, digest: str) -> str:
    clean_term = urllib.parse.quote(term)
    route_paths = {
        "data_keyword": f"data/{clean_term}",
        "shanghai_yearbook_org": f"shnh/whzk/webapi/org/list?freetext={clean_term}&pageth=1&pageSize=8",
        "event_knowledge": f"webapi/hsly/route/getEventList?eventFreeText={clean_term}&pageth=1&pageSize=8",
        "place_names_culture": f"shnh/dmz/webapi/geonames/list?type=4&freetext={clean_term}&pageth=1&pageSize=8",
        "roads_place_names": f"shnh/wkl/webapi/road/list?freetext={clean_term}&type=2&pageth=1&pageSize=8",
        "ancient_book_engravers": f"webapi/kg/list?freetext={clean_term}&pageNum=1",
    }
    path = route_paths.get(route_name, route_name)
    return f"shlib-api://{path}#record={digest}"


def safe_slug(value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]
    clean = "".join(ch if ch.isalnum() else "-" for ch in value.lower())[:42].strip("-")
    return f"{clean}-{digest}"
