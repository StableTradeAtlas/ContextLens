from __future__ import annotations

import json
import os
import ssl
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.library_client import ShanghaiLibraryClient, canonical_source_uri, payload_items, verified_ssl_context
from app.deepseek_client import build_place_interpretation_prompt, parse_interpretation_response
from app.historical_maps import build_experience, historical_map_payload
from app.memory_web import HTML, sanitize_legacy_audit_log, write_private_audit
from app.models import HistoricalFeature
from app.place_investigation import (
    FALLBACK_CANDIDATES,
    FALLBACK_FEATURES,
    InvestigationStore,
    build_archive_network,
    build_place_claims,
    investigate_address,
    merge_candidates,
    normalize_architecture,
    normalize_event,
    normalize_road_candidate,
    parse_public_address,
    resolve_place,
)


def test_official_adapter_field_normalization() -> None:
    road = normalize_road_candidate(
        {
            "nameChs": "霞飞路",
            "historyOf": "http://data.library.sh.cn/entity/road/kzourann5jxemeiz",
            "historyOfName": "泰山路",
            "temporalValue": "~1943.10.10",
            "uri": "http://data.library.sh.cn/entity/road/vus34wj1kewtloqv",
        },
        "霞飞路",
        "436号",
        1934,
    )
    assert road is not None
    assert road.valid_to == 1943
    assert road.house_number == "436号"
    assert road.official_uri.startswith("https://data.library.sh.cn/")

    event = normalize_event(
        {
            "title": "康健书局创办",
            "description": "康健书局设于霞飞路（今淮海中路）436号。",
            "dateLabel": "1934年至1950年",
            "begin": "1934-01-01",
            "end": "1950-12-31",
            "uri": "http://data.library.sh.cn/authority/event/04jaae3kvaff22d1",
        },
        ["霞飞路", "淮海中路"],
    )
    assert event is not None
    assert (event.start_year, event.end_year) == (1934, 1950)
    assert event.address == "霞飞路436号"

    numbered_address = normalize_event(
        {
            "title": "某机构迁入",
            "description": "机构迁入淮海中路1843号。",
            "dateLabel": "1988年",
            "begin": "1988-01-01",
            "end": "1988-12-31",
            "uri": "http://data.library.sh.cn/authority/event/year-guard",
        },
        ["淮海中路"],
    )
    assert numbered_address is not None
    assert (numbered_address.start_year, numbered_address.end_year) == (1988, 1988)

    building = normalize_architecture(
        {
            "nameS": "上海市第一百货商店",
            "address": "南京东路330号",
            "road": "南京东路",
            "des": "上海优秀历史建筑。",
            "long": "121.49024",
            "lat": "31.243027",
            "uri": "http://data.library.sh.cn/entity/architecture/71lebilu80bbmb5n",
        },
        ["南京东路"],
    )
    assert building is not None
    assert building.spatial_precision == "source_coordinate"
    assert building.longitude == 121.49024


def test_payload_and_jsonld_uri_helpers() -> None:
    rows = [{"@id": "one"}, {"@id": "two"}]
    assert payload_items({"resultList": rows}) == rows
    assert canonical_source_uri("http://data.library.sh.cn/authority/event/abc") == "https://data.library.sh.cn/authority/event/abc"


def test_old_name_resolution_and_flagship_timeline() -> None:
    parsed = parse_public_address("霞飞路436号，约1934年")
    assert parsed["place_term"] == "霞飞路"
    assert parsed["house_number"] == "436号"
    resolution = resolve_place("霞飞路436号", "1930年代", allow_live=False)
    assert resolution["status"] == "resolved"
    candidate = resolution["candidates"][0]
    assert "淮海中路" in candidate["modern_names"]
    assert [item["name"] for item in candidate["name_periods"]] == ["西江路", "宝昌路", "霞飞路", "泰山路", "林森中路", "淮海中路"]
    result = investigate_address(candidate, address="霞飞路436号", era_hint="1930年代", allow_live=False)
    event = next(item for item in result["timeline"] if item["title"] == "康健书局创办")
    assert event["start_year"] == 1934
    assert result["query"]["focus_year"] == 1934
    assert not (event["start_year"] <= 1920 <= event["end_year"])
    assert any("436" in item["address"] for item in result["evidence"])


def test_arbitrary_year_map_catalog_and_landmark_models() -> None:
    maps = historical_map_payload(1888)
    assert maps["min_year"] == 1600
    assert maps["max_year"] >= 2026
    assert len(maps["catalog"]) >= 20
    assert maps["dynamic_layer"]["style_url"].startswith("https://www.openhistoricalmap.org/")
    assert maps["nearest_maps"][0]["year"] in {1884, 1904}
    assert any(item["year"] == 1934 for item in maps["catalog"])
    assert any(item["model_id"] == "customs-house" for item in maps["landmark_models"])
    assert "id=\"yearInput\"" in HTML
    assert "id=\"historyMap\"" in HTML and "id=\"modernMap\"" in HTML
    assert "maplibre-gl-dates.js" in HTML


def test_nanjing_ambiguity_and_negative_case() -> None:
    ambiguous = resolve_place("南京路百货公司", "1940年代", allow_live=False)
    assert ambiguous["status"] == "ambiguous"
    assert ambiguous["candidates"][0]["canonical_name"] == "南京东路"
    assert {item["canonical_name"] for item in ambiguous["candidates"]} >= {"南京东路", "南京西路"}

    missing = resolve_place("火星路9999号", "1930年代", allow_live=False)
    assert missing["status"] == "unresolved"
    assert missing["candidates"] == []
    assert "不会据此编造历史" in missing["guidance"]


def test_expanded_curated_place_coverage_uses_official_entities() -> None:
    cases = {
        "贝当路311号": "衡山路",
        "静安寺路1025弄": "南京西路",
        "北四川路85号": "四川北路",
        "福州路390号": "福州路",
        "窦乐安路59号": "多伦路",
        "施高塔路85弄": "山阴路",
    }
    assert len(FALLBACK_CANDIDATES) >= 22
    for address, expected in cases.items():
        resolution = resolve_place(address, "1930年代", allow_live=False)
        assert resolution["status"] == "resolved"
        candidate = resolution["candidates"][0]
        assert candidate["canonical_name"] == expected
        assert candidate["source_uri"].startswith("https://data.library.sh.cn/entity/road/")
        result = investigate_address(candidate, address=address, era_hint="1930年代", allow_live=False)
        assert len(result["evidence"]) >= 2
        building_evidence = [item for item in result["evidence"] if item["feature_type"] == "building"]
        assert building_evidence
        assert all(item["source_uri"].startswith("https://data.library.sh.cn/entity/architecture/") for item in building_evidence)
        assert any(item["feature_type"] == "road_identity" for item in result["evidence"])

    live_old_name = normalize_road_candidate(
        {
            "nameChs": "海格路",
            "historyOfName": "华山路",
            "temporalValue": "~1943.10.10",
            "uri": "http://data.library.sh.cn/entity/road/dbg5p115zojjx0sa",
        },
        "海格路",
        "922号",
        1930,
    )
    assert live_old_name is not None
    merged = merge_candidates([live_old_name], FALLBACK_CANDIDATES["华山路"])
    assert len(merged) == 1
    assert merged[0].canonical_name == "华山路"
    assert merged[0].name_periods[0]["name"] == "海格路"


def test_snapshot_driven_route_breadth() -> None:
    """A broad official road set must complete offline, not just one demo route."""
    full_routes = [
        "华山路", "南京西路", "四川北路", "多伦路", "安福路", "复兴西路",
        "巨鹿路", "常熟路", "延安中路", "新乐路", "福州路", "衡山路",
        "重庆南路", "长阳路", "陕西南路", "黄陂南路", "南昌路", "绍兴路",
        "茂名南路", "江西中路", "复兴中路",
    ]
    for road in full_routes:
        resolution = resolve_place(road, allow_live=False)
        assert resolution["status"] == "resolved", road
        result = investigate_address(resolution["candidates"][0], address=road, allow_live=False)
        assert result["timeline"], road
        assert len(result["evidence"]) >= 2, road


def test_director_maps_models_and_interactions_stay_evidence_bounded() -> None:
    candidate = FALLBACK_CANDIDATES["霞飞路"][0]
    experience = build_experience(candidate, FALLBACK_FEATURES["霞飞路"])
    assert experience["default_duration_seconds"] == 20
    assert experience["duration_options"] == [20, 30, 45]
    assert sum(item["duration_ms"] for item in experience["chapters"]) == 45_000
    assert len(experience["historical_maps"]) == 4
    assert all(item["source_url"] and item["license"] and item["attribution"] for item in experience["historical_maps"])
    # The review-only control-point draft must not be presented as a measured,
    # georeferenced overlay.
    princeton = next(item for item in experience["historical_maps"] if item["map_id"] == "princeton-1943")
    assert princeton["overlay_status"] == "review_only"
    assert princeton["rms_error_m"] is None
    assert all(item["evidence_ids"] for item in experience["chapters"])
    assert all(item["evidence_ids"] for item in experience["interactions"])
    assert {item["reconstruction_level"] for item in experience["landmark_scenes"]} <= {"A", "B", "C"}
    assert all(item["source_uri"] and item["reconstruction_note"] for item in experience["landmark_scenes"])
    assert experience["privacy"] == {"memory_uploaded": False, "memory_in_url": False, "stamps_storage": "sessionStorage"}

    generic = build_experience(FALLBACK_CANDIDATES["衡山路"][0], FALLBACK_FEATURES["衡山路"])
    assert sum(item["duration_ms"] for item in generic["chapters"]) == 45_000
    assert len(generic["chapters"]) == 2
    assert generic["chapters"][0]["center"] != [121.4737, 31.2231]

    second_ring = {
        "海格路922号": "华山路",
        "巨泼来斯路255号": "安福路",
        "巨籁达路889号": "巨鹿路",
        "善钟路209号": "常熟路",
        "亨利路55号": "新乐路",
        "华德路62号": "长阳路",
        "中正中路913弄": "延安中路",
    }
    for address, canonical in second_ring.items():
        resolution = resolve_place(address, "1930年代", allow_live=False)
        assert resolution["status"] == "resolved"
        assert resolution["candidates"][0]["canonical_name"] == canonical


def test_frontend_privacy_and_explicit_scope_boundaries() -> None:
    source = (Path(__file__).resolve().parents[1] / "frontend" / "src" / "main.ts").read_text(encoding="utf-8")
    investigation_call = source[source.index('api("/api/investigations"'):source.index('api("/api/investigations"') + 420]
    assert "memory" not in investigation_call
    assert "navigator.geolocation" not in source
    assert "getUserMedia" not in source
    assert 'api("/api/catalog")' in source
    assert "Filter the completed street dossiers" in source
    assert "年代待考" not in source
    assert "SOURCE PASSPORT" not in source
    assert "eraInput" not in source
    assert "supporting source" in source
    assert "/interpret" not in source


def test_archive_network_keeps_people_and_institutions_evidence_bound() -> None:
    event = normalize_event(
        {
            "title": "康健书局创办",
            "description": "康健书局设址霞飞路436号，经理陈振民。",
            "dateLabel": "1934年",
            "uri": "http://data.library.sh.cn/authority/event/04jaae3kvaff22d1",
            "organizationList": [{"label": "康健书局", "uri": ""}],
        },
        ["霞飞路"],
    )
    assert event is not None
    assert event.people == ["陈振民"]
    assert "康健书局" in event.organizations
    people = {
        "陈振民": [
            {"fname": "陈振民", "uri": "http://data.library.sh.cn/entity/person/one"},
            {"fname": "陈振民", "uri": "http://data.library.sh.cn/entity/person/two"},
        ]
    }
    organizations = {
        "康健书局": [{"name": ["康健书局@chs", "kangjianshuju@en"], "uri": "http://data.library.sh.cn/entity/organization/kangjian", "noteOfSource": "年谱事件库"}]
    }
    network = build_archive_network(FALLBACK_CANDIDATES["霞飞路"][0], [event], people, organizations)
    person = network["people"][0]
    assert person["match_status"] == "ambiguous"
    assert person["source_uri"] == ""
    assert "同名" in person["description"]
    organization = network["organizations"][0]
    assert organization["match_status"] == "confirmed"
    assert organization["source_uri"].endswith("/kangjian")
    assert all(link["evidence_ids"] for link in network["links"])


def test_optional_deepseek_prompt_and_citations_are_evidence_gated() -> None:
    prompt, allowed = build_place_interpretation_prompt(
        question="这里发生过什么？",
        language="zh",
        place_name="霞飞路",
        year=1934,
        evidence_cards=[{"evidence_id": "event-one", "title": "事件", "description": "公开证据", "source_title": "上海图书馆"}],
        archive_network={"links": [{"source": "place", "target": "event", "relation": "发生于", "evidence_ids": ["event-one"]}], "people": [], "organizations": []},
    )
    assert allowed == {"event-one"}
    assert "公开证据" in prompt
    assert "我的记忆" not in prompt
    parsed = parse_interpretation_response(
        json.dumps({"answer": "有一条可核查事件。", "evidence_ids": ["event-one", "invented"], "uncertainties": ["人物待考"], "follow_up_questions": []}, ensure_ascii=False),
        allowed,
    )
    assert parsed["evidence_ids"] == ["event-one"]


def test_relation_gate_and_evidence_deletion_downgrade() -> None:
    candidate = FALLBACK_CANDIDATES["霞飞路"][0]
    unrelated = HistoricalFeature(
        feature_id="unrelated",
        feature_type="event",
        title="慈善电影放映",
        description="一场发生在上海的慈善电影活动。",
        source_uri="https://example.invalid/source",
        source_title="测试来源",
        start_year=1934,
        evidence_ids=["unrelated"],
    )
    unrelated_claim = build_place_claims(candidate, [unrelated])[0]
    assert unrelated_claim.support_level == "context"
    assert unrelated_claim.audit_status == "review"

    features = FALLBACK_FEATURES["霞飞路"][:2]
    full_claims = build_place_claims(candidate, features)
    assert any(claim.claim_id == "claim-place-synthesis" for claim in full_claims)
    after_deletion = build_place_claims(candidate, features[:1])
    assert not any(claim.claim_id == "claim-place-synthesis" for claim in after_deletion)
    assert all("building-guotai" not in claim.evidence_ids for claim in after_deletion)


def test_verified_tls_and_private_audit_log() -> None:
    context = verified_ssl_context()
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True

    import app.memory_web as memory_web

    original = memory_web.LOG_DIR
    with tempfile.TemporaryDirectory() as folder:
        memory_web.LOG_DIR = Path(folder)
        payload = {
            "address": "霞飞路436号",
            "memory": "外婆说这里有一家亮灯的书店",
            "api_key": "never-log-this-secret",
            "mode": "place_memory",
        }
        write_private_audit(payload, {"evidence": [{"id": "one"}]})
        text = (Path(folder) / "query_audit.jsonl").read_text(encoding="utf-8")
        record = json.loads(text)
        assert record["query_hash"]
        assert "霞飞路436号" not in text
        assert payload["memory"] not in text
        assert payload["api_key"] not in text
    memory_web.LOG_DIR = original


def test_verified_cache_survives_network_failure_without_leaking_key() -> None:
    import app.library_client as library_client

    class OfflineOpener:
        def open(self, request, timeout=0):
            raise TimeoutError("offline")

    original = library_client.RAW_DIR
    with tempfile.TemporaryDirectory() as folder:
        library_client.RAW_DIR = Path(folder)
        client = ShanghaiLibraryClient("top-secret-key", request_interval=0, cache_ttl=0)
        url = "https://data1.library.sh.cn/example?freetext=test&key=top-secret-key"
        path = client._cache_path(url)
        path.write_text('{"data":[{"name":"cached"}]}', encoding="utf-8")
        os.utime(path, (1, 1))
        client.opener = OfflineOpener()
        payload = client._get_json_or_text(url)
        assert payload["data"][0]["name"] == "cached"
        assert "top-secret-key" not in path.name
        assert "top-secret-key" not in path.read_text(encoding="utf-8")
    library_client.RAW_DIR = original


def test_legacy_audit_log_is_migrated_to_hashes() -> None:
    import app.memory_web as memory_web

    original = memory_web.LOG_DIR
    with tempfile.TemporaryDirectory() as folder:
        memory_web.LOG_DIR = Path(folder)
        path = Path(folder) / "query_audit.jsonl"
        path.write_text(json.dumps({"question": "南京路百货公司", "memory": "私人回忆"}, ensure_ascii=False) + "\n", encoding="utf-8")
        sanitize_legacy_audit_log()
        text = path.read_text(encoding="utf-8")
        assert "南京路百货公司" not in text
        assert "私人回忆" not in text
        assert json.loads(text)["query_hash"]
    memory_web.LOG_DIR = original


def test_real_investigation_states_and_browser_only_memory_contract() -> None:
    store = InvestigationStore()
    candidate = resolve_place("霞飞路436号", "1930年代", allow_live=False)["candidates"][0]
    created = store.create({"address": "霞飞路436号", "era_hint": "1930年代", "candidate": candidate, "allow_live": False})
    assert created["status"] in {"queued", "resolving", "fetching", "linking", "auditing", "complete"}
    deadline = time.monotonic() + 3
    job = created
    while job["status"] not in {"complete", "failed"} and time.monotonic() < deadline:
        time.sleep(0.02)
        job = store.get(created["id"])
    assert job is not None and job["status"] == "complete"
    assert job["result"]["quality"]["fallback_feature_count"] >= 3
    assert 'JSON.stringify({address,era_hint:' in HTML
    assert 'JSON.stringify({address,era_hint:$("eraInput").value,memory:' not in HTML


if __name__ == "__main__":
    test_official_adapter_field_normalization()
    test_payload_and_jsonld_uri_helpers()
    test_old_name_resolution_and_flagship_timeline()
    test_arbitrary_year_map_catalog_and_landmark_models()
    test_nanjing_ambiguity_and_negative_case()
    test_expanded_curated_place_coverage_uses_official_entities()
    test_snapshot_driven_route_breadth()
    test_director_maps_models_and_interactions_stay_evidence_bounded()
    test_frontend_privacy_and_explicit_scope_boundaries()
    test_relation_gate_and_evidence_deletion_downgrade()
    test_verified_tls_and_private_audit_log()
    test_verified_cache_survives_network_failure_without_leaking_key()
    test_legacy_audit_log_is_migrated_to_hashes()
    test_real_investigation_states_and_browser_only_memory_contract()
    print("place investigation tests passed")
