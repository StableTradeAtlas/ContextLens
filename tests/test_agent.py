from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import answer_question
from app.agent import openable_source_url
from app.ingest import ingest
from app.models import EvidenceRecord
from app.retrieval import retrieve
from app.storage import count_records, get_record


def test_agent_returns_cited_answer() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    result = answer_question("淮海中路有哪些上海优秀历史建筑？", mode="explore_place")
    assert result["citations"]
    assert result["audit"]["evidence_count"] > 0
    assert result["evidence_cards"][0]["lineage"]["source_mode"] == "verified_official_snapshot"


def test_agent_supports_mvp_options() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    result = answer_question(
        "淮海中路的历史建筑可以形成怎样的地点档案？",
        language="zh",
        mode="explore_place",
        output_style="investigation_dossier",
    )
    assert result["language"] == "zh"
    assert result["mode"] == "explore_place"
    assert result["evidence_cards"][0]["record_id"]
    assert result["audit"]["latency_ms"] is not None
    assert result["research_profile"]
    assert result["source_timeline"]
    assert result["topic_signals"]
    assert result["next_steps"]
    assert result["answer_sections"]
    assert result["mode_profile"]["label"]
    assert result["deepseek_assist"]["status"] == "disabled"


def test_output_styles_change_answer_structure() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    question = "近代海关、口岸和银行制度如何影响中国跨境贸易？"
    timeline = answer_question(question, language="zh", mode="treaty_ports", output_style="timeline")
    analogy = answer_question(question, language="zh", mode="treaty_ports", output_style="policy_analogy")
    timeline_titles = [section["title"] for section in timeline["answer_sections"]]
    analogy_titles = [section["title"] for section in analogy["answer_sections"]]
    assert timeline_titles != analogy_titles
    assert "围绕问题的时间线判断" in timeline_titles
    assert "问题中的类比对象" in analogy_titles


def test_different_questions_get_targeted_sections() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    customs = answer_question("近代海关和通商口岸怎样改变跨境贸易治理？", language="zh", mode="treaty_ports")
    currency = answer_question("历史上的票号和银行如何支撑跨区域结算信用？", language="zh", mode="currency_settlement")
    customs_text = " ".join(section["body"] for section in customs["answer_sections"])
    currency_text = " ".join(section["body"] for section in currency["answer_sections"])
    assert customs["question_analysis"]["intent"] in {"mechanism", "impact"}
    assert currency["question_analysis"]["intent"] == "mechanism"
    assert "海关" in customs_text or "口岸" in customs_text
    assert "票号" in currency_text or "银行" in currency_text
    assert customs_text != currency_text


def test_retrieval_prioritizes_question_relevance_over_live_status() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    results = retrieve("淮海中路有哪些上海优秀历史建筑？", top_k=6, mode="explore_place")
    assert results
    assert all(
        "淮海中路" in " ".join(
            [
                result.record.title,
                result.record.snippet,
                " ".join(result.record.places),
                " ".join(result.record.topics),
                str(result.record.raw.get("des", "")),
                str(result.record.raw.get("address", "")),
            ]
        )
        for result in results[:3]
    )
    assert all(result.record.lineage.get("source_mode") == "verified_official_snapshot" for result in results)


def test_answer_reports_evidence_fit_and_support_strength() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    result = answer_question("淮海中路有哪些上海优秀历史建筑？", language="zh", mode="explore_place")
    assert result["evidence_fit"]["total_cards"] > 0
    assert result["evidence_fit"]["level"] in {"medium", "strong"}
    assert "历史建筑" in result["evidence_fit"]["covered_terms"]
    assert result["evidence_cards"][0]["support_strength"] == "直接支撑"
    assert "地名" in " ".join(section["body"] for section in result["answer_sections"])


def test_source_urls_prefer_specific_records_over_generic_portal() -> None:
    entity = EvidenceRecord(
        record_id="entity-test",
        title="上海通商海关造册处",
        snippet="entity test",
        source="Shanghai Library Open Data API",
        source_uri="http://data.library.sh.cn/entity/organization/n8mqs6ixus42z3yz",
        dataset="test",
    )
    fallback = EvidenceRecord(
        record_id="fallback-test",
        title="demo fallback",
        snippet="fallback test",
        source="demo",
        source_uri="https://www.library.sh.cn/resource?type=%E5%8E%86%E5%8F%B2%E6%96%87%E7%8C%AE%E8%B5%84%E6%BA%90",
        dataset="demo_seed",
    )
    assert openable_source_url(entity) == "https://data.library.sh.cn/entity/organization/n8mqs6ixus42z3yz"
    assert openable_source_url(fallback) == "/source/fallback-test"


def test_answer_cards_do_not_use_generic_library_portal_as_open_url() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    result = answer_question("近代海关和通商口岸怎样改变跨境贸易治理？", language="zh", mode="treaty_ports")
    assert result["evidence_cards"]
    assert not any(
        str(card["open_url"]).startswith("https://www.library.sh.cn/resource?type=")
        for card in result["evidence_cards"]
    )


def test_get_record_returns_official_snapshot_record() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    record = retrieve("淮海中路历史建筑", top_k=1, mode="explore_place")[0].record
    stored = get_record(record.record_id)
    assert stored is not None
    assert not stored.is_live_api
    assert stored.lineage.get("source_mode") == "verified_official_snapshot"


def test_finance_boundary_is_guarded() -> None:
    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)
    result = answer_question("稳定价值数字结算是否适合直接投资或支付部署？", language="zh")
    assert result["audit"]["financial_advice_check"] == "guarded"


def test_contextlens_returns_investigation_dossier() -> None:
    ingest(use_live=False, seed_if_empty=True)
    result = answer_question(
        "盛宣怀与上海的铁路、银行和航运有什么联系？",
        language="zh",
        mode="trace_person",
        output_style="investigation_dossier",
    )
    investigation = result["investigation"]
    assert result["one_line_finding"]
    assert investigation["task"]["key"] == "trace_person"
    assert investigation["entities"]
    assert investigation["claims"]
    assert investigation["counter_evidence"]
    assert investigation["replay"]
    assert investigation["receipt"]["claims_checked"] == len(investigation["claims"])
    assert investigation["graph"]["nodes"]
    assert investigation["graph"]["links"]
    assert investigation["timeline_events"]
    assert investigation["relationship_network"]["links"]
    assert investigation["spatial_traces"]
    assert investigation["story_mode"]["public_narrative"]
    assert investigation["research_mode"]["citation_protocol"]
    assert investigation["quality_gates"]
    assert investigation["follow_up_routes"]


def test_public_task_modes_are_supported() -> None:
    ingest(use_live=False, seed_if_empty=True)
    examples = {
        "trace_person": "鲁迅在上海期间与哪些人物、地点和刊物相关？",
        "explore_place": "外滩某栋历史建筑经历过哪些机构和人物？",
        "reconstruct_event": "近代上海通商事件如何连接海关、商人和银行？",
        "read_document": "一条近代报刊索引如何追溯到人物、地点和事件？",
        "city_memory": "南京路的百货公司、报刊广告和市民生活可以串成怎样的城市记忆路线？",
        "family_memory": "如果我只知道家谱中的一个姓名和上海旧地址，下一步该查哪些证据？",
        "shanghai_world": "一张汇票如何连接商人、银行、口岸与海外贸易？",
    }
    for mode, question in examples.items():
        result = answer_question(question, language="zh", mode=mode, output_style="investigation_dossier", top_k=4)
        assert result["mode"] == mode
        assert result["investigation"]["task"]["key"] == mode
        assert result["data_receipt"]["records_examined"] >= 0


def test_contextlens_public_modes_have_award_readiness_and_source_passports() -> None:
    ingest(use_live=False, seed_if_empty=True)
    result = answer_question(
        "张爱玲的作品、出版机构和上海公寓能如何形成文学地景档案？",
        language="zh",
        mode="city_memory",
        output_style="investigation_dossier",
    )
    assert result["mode"] == "city_memory"
    assert result["award_readiness"]["overall_score"] > 0
    assert result["award_readiness"]["items"]
    assert result["professional_briefing"]
    assert result["data_receipt"]["evidence_types"]
    assert result["data_receipt"]["public_tags"]
    assert result["evidence_cards"][0]["evidence_type"]
    assert result["evidence_cards"][0]["provenance_note"]
    assert result["evidence_cards"][0]["verification_notes"]
    gate_keys = {gate["key"] for gate in result["investigation"]["quality_gates"]}
    assert "public_reuse" in gate_keys


def test_expanded_demo_seed_pool_prefers_relevance_over_card_quota() -> None:
    ingest(use_live=False, seed_if_empty=True)
    assert count_records() >= 54
    result = answer_question(
        "南京路、报刊广告、百货公司和城市公共生活之间有哪些证据联系？",
        language="zh",
        mode="city_memory",
        output_style="investigation_dossier",
    )
    # The place-first upgrade deliberately stops filling an arbitrary card
    # quota when the remaining material does not directly fit the question.
    assert 1 <= len(result["evidence_cards"]) <= 8
    assert result["data_receipt"]["records_examined"] == len(result["evidence_cards"])
    assert all(card["support_strength"] == "直接支撑" for card in result["evidence_cards"])


if __name__ == "__main__":
    test_agent_returns_cited_answer()
    test_agent_supports_mvp_options()
    test_output_styles_change_answer_structure()
    test_different_questions_get_targeted_sections()
    test_retrieval_prioritizes_question_relevance_over_live_status()
    test_answer_reports_evidence_fit_and_support_strength()
    test_source_urls_prefer_specific_records_over_generic_portal()
    test_answer_cards_do_not_use_generic_library_portal_as_open_url()
    test_get_record_returns_official_snapshot_record()
    test_finance_boundary_is_guarded()
    test_contextlens_returns_investigation_dossier()
    test_public_task_modes_are_supported()
    test_contextlens_public_modes_have_award_readiness_and_source_passports()
    test_expanded_demo_seed_pool_prefers_relevance_over_card_quota()
    print("smoke test passed")
