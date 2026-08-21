from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agent import answer_question
from app.ingest import ingest
from app.storage import count_records


DEFAULT_QUESTION = "盛宣怀与上海的铁路、银行和航运有什么联系？"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a ContextLens demo investigation.")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    parser.add_argument("--mode", default="trace_person")
    parser.add_argument("--output-style", default="investigation_dossier")
    parser.add_argument("--deepseek", action="store_true", help="Enable optional DeepSeek fast assist if configured.")
    args = parser.parse_args()

    if count_records() == 0:
        ingest(use_live=False, seed_if_empty=True)

    answer = answer_question(
        args.question,
        top_k=10,
        language=args.language,
        mode=args.mode,
        output_style=args.output_style,
        use_deepseek=args.deepseek,
    )
    print("\nContextLens Demo Investigation")
    print("=" * 72)
    print(f"Clue: {answer['question']}")
    if answer.get("one_line_finding"):
        print(f"\nOne-Line Finding:\n{answer['one_line_finding']}")
    award = answer.get("award_readiness") or {}
    if award.get("overall_score") is not None:
        print(f"\nAward Readiness: {award.get('overall_score')}/100 ({award.get('level_label', '')})")
        for item in award.get("items", [])[:6]:
            print(f"- {item.get('title')}: {item.get('score')}/100 | {item.get('detail')}")
    investigation = answer.get("investigation") or {}
    receipt = investigation.get("receipt") or {}
    if receipt.get("summary"):
        print(f"\nData-Use Receipt:\n{receipt['summary']}")
    briefing = answer.get("professional_briefing") or []
    if briefing:
        print("\nProfessional Research Design:")
        for item in briefing[:6]:
            print(f"- {item.get('title')}: {item.get('body')}")
    if investigation.get("timeline_events"):
        print("\nHistorical Timeline:")
        for event in investigation["timeline_events"][:5]:
            print(f"- {event['date']} | {event['title']} [{event['support_label']}]")
    network = investigation.get("relationship_network") or {}
    if network.get("summary"):
        print(f"\nRelationship Network:\n{network['summary']}")
        for link in network.get("links", [])[:5]:
            print(f"- {link.get('source_label', link.get('source'))} -> {link.get('target_label', link.get('target'))}: {link.get('relation')}")
    if investigation.get("spatial_traces"):
        print("\nSpatial Trace:")
        for trace in investigation["spatial_traces"][:5]:
            print(f"- {trace['place']} | {trace['coordinates_status']} | evidence={len(trace.get('evidence_ids', []))}")
    story = investigation.get("story_mode") or {}
    if story.get("public_narrative"):
        print(f"\nStory Mode:\n{story['public_narrative']}")
    research = investigation.get("research_mode") or {}
    if research.get("citation_protocol"):
        print(f"\nResearch Mode:\n{research['citation_protocol']}")
    if investigation.get("quality_gates"):
        print("\nEvidence Quality Gates:")
        for gate in investigation["quality_gates"]:
            print(f"- [{gate['status_label']}] {gate['title']}: {gate['detail']}")
    if investigation.get("follow_up_routes"):
        print("\nFollow-Up Routes:")
        for route in investigation["follow_up_routes"][:4]:
            print(f"- {route['question']}")
    print(f"\nProblem Summary:\n{answer['problem_summary']}")
    print("\nTop Evidence Cards:")
    for idx, citation in enumerate(answer["citations"][:4], start=1):
        print(f"{idx}. {citation['title']} [{citation['dataset']}; {citation.get('evidence_type', '')}; score={citation['score']}]")
        print(f"   {citation['uri']}")
        for note in citation.get("verification_notes", [])[:2]:
            print(f"   Review: {note}")
    print(f"\nOutput Style: {answer.get('output_style_label', answer['output_style'])}")
    print("\nStructured Sections:")
    for section in answer.get("answer_sections", []):
        print(f"\n## {section['title']}\n{section['body']}")
    if investigation.get("claims"):
        print("\nClaim Ledger:")
        for claim in investigation["claims"][:6]:
            print(f"- [{claim['support_label']} / {claim['status']}] {claim['text']}")
    assist = answer.get("deepseek_assist") or {}
    if assist.get("status") == "ok":
        print(f"\nDeepSeek Fast Assist:\n{assist.get('content', '')}")
    print("\nFuture Questions:")
    for q in answer["future_questions"]:
        print(f"- {q}")
    print("\nAudit:")
    for key, value in answer["audit"].items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
