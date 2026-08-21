from __future__ import annotations

import os
import json
import re
from typing import Any
import urllib.error
import urllib.request

from app.library_client import verified_ssl_context


DEEPSEEK_CHAT_URL = "https://api.deepseek.com/chat/completions"


def interpret_place_archive(
    *,
    api_key: str | None,
    model: str,
    question: str,
    language: str,
    place_name: str,
    year: int | None,
    evidence_cards: list[dict[str, Any]],
    archive_network: dict[str, Any],
) -> dict[str, Any]:
    """Optional, user-triggered interpretation over public evidence only."""
    if not api_key:
        return {"enabled": False, "status": "not_configured", "answer": "", "evidence_ids": [], "uncertainties": []}
    prompt, allowed_ids = build_place_interpretation_prompt(
        question=question,
        language=language,
        place_name=place_name,
        year=year,
        evidence_cards=evidence_cards,
        archive_network=archive_network,
    )
    body = json.dumps({
        "model": model or "deepseek-chat",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are the optional archive interpreter inside ContextLens 文脉镜. "
                    "Use only the supplied public Shanghai Library evidence. Never infer a person identity from an ambiguous same-name match. "
                    "Do not add outside facts or URLs. Unknown means unknown. Return one JSON object only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": int(os.environ.get("DEEPSEEK_PLACE_MAX_TOKENS", "760")),
        "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        os.environ.get("DEEPSEEK_API_URL", DEEPSEEK_CHAT_URL),
        data=body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        urllib.request.HTTPSHandler(context=verified_ssl_context()),
    )
    try:
        with opener.open(request, timeout=float(os.environ.get("DEEPSEEK_TIMEOUT", "12"))) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        parsed = parse_interpretation_response(content, allowed_ids)
        parsed.update({"enabled": True, "status": "ok", "model": model})
        return parsed
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "status": "error",
            "model": model,
            "answer": "",
            "evidence_ids": [],
            "uncertainties": ["模型解读暂不可用；原始证据仍可继续浏览。"],
            "error_type": type(exc).__name__,
        }


def build_place_interpretation_prompt(
    *,
    question: str,
    language: str,
    place_name: str,
    year: int | None,
    evidence_cards: list[dict[str, Any]],
    archive_network: dict[str, Any],
) -> tuple[str, set[str]]:
    evidence_payload: list[dict[str, Any]] = []
    allowed_ids: set[str] = set()
    for card in evidence_cards[:16]:
        evidence_id = str(card.get("evidence_id") or "")
        if not evidence_id:
            continue
        allowed_ids.add(evidence_id)
        evidence_payload.append({
            "evidence_id": evidence_id,
            "title": card.get("title"),
            "description": str(card.get("description") or "")[:620],
            "source_title": card.get("source_title"),
            "time_label": card.get("time_label"),
            "feature_type": card.get("feature_type"),
            "people": card.get("people", []),
            "organizations": card.get("organizations", []),
        })
    relation_payload = [{
        "source": item.get("source"),
        "target": item.get("target"),
        "relation": item.get("relation"),
        "evidence_ids": item.get("evidence_ids", []),
    } for item in (archive_network.get("links") or [])[:24]]
    ambiguity_payload = [{
        "name": item.get("name"),
        "type": item.get("node_type"),
        "match_status": item.get("match_status"),
        "candidate_count": item.get("candidate_count", 0),
    } for item in (archive_network.get("people") or []) + (archive_network.get("organizations") or [])]
    schema = {
        "answer": "concise evidence-grounded answer",
        "evidence_ids": ["only IDs from the supplied list"],
        "uncertainties": ["remaining uncertainty"],
        "follow_up_questions": ["up to three evidence-oriented questions"],
    }
    return (
        f"Language: {language}\nPlace: {place_name}\nSelected year: {year or 'unspecified'}\n"
        f"User question: {question[:320]}\n\n"
        "Rules: cite every historical statement with evidence_ids; do not use personal memory; "
        "do not turn ambiguous name matches into biographies; if evidence is insufficient, say so.\n"
        f"Required JSON schema: {json.dumps(schema, ensure_ascii=False)}\n\n"
        f"Evidence cards: {json.dumps(evidence_payload, ensure_ascii=False)}\n\n"
        f"Evidence-bound relations: {json.dumps(relation_payload, ensure_ascii=False)}\n\n"
        f"Identity audit: {json.dumps(ambiguity_payload, ensure_ascii=False)}",
        allowed_ids,
    )


def parse_interpretation_response(content: str, allowed_ids: set[str]) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.IGNORECASE)
    parsed = json.loads(cleaned)
    if not isinstance(parsed, dict) or not str(parsed.get("answer") or "").strip():
        raise ValueError("invalid interpretation payload")
    cited = [str(value) for value in parsed.get("evidence_ids", []) if str(value) in allowed_ids]
    uncertainties = [str(value)[:240] for value in parsed.get("uncertainties", []) if str(value).strip()][:5]
    follow_ups = [str(value)[:180] for value in parsed.get("follow_up_questions", []) if str(value).strip()][:3]
    return {
        "answer": str(parsed["answer"]).strip()[:2400],
        "evidence_ids": list(dict.fromkeys(cited)),
        "uncertainties": uncertainties,
        "follow_up_questions": follow_ups,
    }


def refine_with_deepseek(
    *,
    api_key: str | None,
    model: str,
    question: str,
    language: str,
    mode_label: str,
    output_style_label: str,
    answer_sections: list[dict],
    evidence_cards: list[dict],
    question_analysis: dict | None = None,
    evidence_fit: dict | None = None,
) -> dict[str, Any]:
    if not api_key:
        return {"enabled": False, "status": "not_configured", "content": ""}
    evidence_payload = [
        {
            "title": card.get("title"),
            "date": card.get("date"),
            "matched_terms": card.get("matched_terms", []),
            "relevance": card.get("relevance"),
            "source_url": card.get("open_url") or card.get("uri"),
            "citation": card.get("citation"),
        }
        for card in evidence_cards[:6]
    ]
    section_payload = [{"title": item.get("title"), "body": item.get("body")} for item in answer_sections[:6]]
    prompt = build_prompt(
        question=question,
        language=language,
        mode_label=mode_label,
        output_style_label=output_style_label,
        answer_sections=section_payload,
        evidence_cards=evidence_payload,
        question_analysis=question_analysis or {},
        evidence_fit=evidence_fit or {},
    )
    try:
        body = json.dumps(
            {
                "model": model or "deepseek-chat",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an auxiliary research-writing layer for ContextLens 文脉镜. "
                            "Use only the supplied Shanghai Library evidence cards and the local structured answer. "
                            "Do not introduce external facts, URLs, legal advice, investment advice, or payment implementation advice. "
                            "Use the evidence-fit report to calibrate confidence. If the evidence is insufficient, say so clearly."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": int(os.environ.get("DEEPSEEK_MAX_TOKENS", "620")),
                "stream": False,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            os.environ.get("DEEPSEEK_API_URL", DEEPSEEK_CHAT_URL),
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=float(os.environ.get("DEEPSEEK_TIMEOUT", "10"))) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not content:
            return {"enabled": True, "status": "empty_response", "model": model, "content": ""}
        return {"enabled": True, "status": "ok", "model": model, "content": content}
    except Exception as exc:  # noqa: BLE001
        return {
            "enabled": True,
            "status": "error",
            "model": model,
            "content": "",
            "error": f"{type(exc).__name__}: {exc}",
        }


def build_prompt(
    *,
    question: str,
    language: str,
    mode_label: str,
    output_style_label: str,
    answer_sections: list[dict],
    evidence_cards: list[dict],
    question_analysis: dict,
    evidence_fit: dict,
) -> str:
    if language == "zh":
        instructions = (
            "请基于下面的本地结构化回答和上海图书馆证据卡，生成一段更有针对性的辅助分析。"
            "要求：1）只使用给定证据；2）不要新增未给出的史实；3）保留不确定性；"
            "4）根据证据贴合度调整确定性；5）输出三小节：更针对性的判断、证据约束、下一步追问。"
        )
    else:
        instructions = (
            "Using only the local structured answer and Shanghai Library evidence cards below, produce a more targeted auxiliary analysis. "
            "Requirements: use only supplied evidence, add no external facts, preserve uncertainty, calibrate confidence with the evidence-fit report, and output three mini-sections: "
            "Targeted Reading, Evidence Constraints, Next Question."
        )
    return (
        f"{instructions}\n\n"
        f"Question: {question}\n"
        f"Research mode: {mode_label}\n"
        f"Output style: {output_style_label}\n\n"
        f"Question analysis:\n{question_analysis}\n\n"
        f"Evidence-fit report:\n{evidence_fit}\n\n"
        f"Local structured answer:\n{answer_sections}\n\n"
        f"Shanghai Library evidence cards:\n{evidence_cards}\n"
    )
