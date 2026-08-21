from __future__ import annotations

import re

from app.models import EvidenceRecord, RetrievalResult
from app.storage import load_records


DOMAIN_TERMS = {
    "货币": ["货币", "银", "银两", "纸币", "交子", "会子", "票号", "汇票", "银行", "汇兑", "结算", "信用", "稳定", "stablecoin", "settlement"],
    "贸易": ["贸易", "商路", "丝绸之路", "丝路", "海上丝路", "港口", "口岸", "供应链", "招商", "商人", "通商", "航运", "海外贸易", "信任"],
    "外交": ["外交", "使节", "张骞", "条约", "边疆", "西域", "治理", "政策", "一带一路", "后世文献", "叙事", "belt", "road"],
    "城市记忆": ["城市记忆", "旧地址", "外滩", "南京路", "石库门", "里弄", "历史建筑", "老地图", "老照片", "city walk", "old address", "memory"],
    "公众文化": ["鲁迅", "张爱玲", "宋庆龄", "电影", "影院", "书店", "出版", "报刊", "女性", "职业教育", "公共文化", "literary", "film"],
    "家族线索": ["家谱", "族谱", "人名", "祖籍", "校友录", "旧居", "亲属", "family", "genealogy", "surname"],
    "文献侦探": ["文献", "档案", "古籍", "题跋", "藏书印", "版本", "题名", "索引", "newspaper", "archive"],
    "风险": ["风险", "不确定", "审计", "安全", "合规", "成本", "延迟"],
}

MODE_TERMS = {
    "general": ["货币", "贸易", "外交", "治理", "制度", "证据"],
    "trace_person": ["人物", "传记", "生平", "关系", "机构", "地点", "事件", "盛宣怀", "鲁迅", "张骞", "数字画像"],
    "explore_place": ["地名", "旧址", "旧地址", "道路", "历史建筑", "不可移动文物", "上海", "外滩", "口岸", "空间轨迹", "附近"],
    "reconstruct_event": ["事件", "历史事件", "时间", "地点", "人物", "机构", "因果", "影响", "时间线", "发生"],
    "read_document": ["文献", "题名", "档案", "古籍", "家谱", "报刊", "索引", "版本", "出处"],
    "city_memory": ["城市记忆", "旧地址", "地名", "道路", "外滩", "南京路", "石库门", "里弄", "老地图", "老照片", "城市漫游", "公共文化"],
    "family_memory": ["家谱", "族谱", "人名", "祖籍", "校友录", "旧居", "亲属", "旧地址", "人物关系", "文献", "寻亲"],
    "shanghai_world": ["上海", "世界", "货币", "口岸", "商人", "海关", "银行", "票号", "汇票", "汇兑", "航运", "海外贸易", "全球贸易"],
    "currency_settlement": ["货币", "结算", "银两", "银", "纸币", "交子", "会子", "银行", "票号", "汇兑", "信用", "稳定价值"],
    "treaty_ports": ["近代", "上海", "通商口岸", "口岸", "海关", "关税", "银行", "航运", "保险", "外贸", "商行"],
    "silk_road": ["丝绸之路", "海上丝路", "商路", "张骞", "西域", "中亚", "使节", "边疆", "外交", "商人网络", "多币种", "信任"],
    "dynastic_history": ["唐", "宋", "元", "明", "清", "王朝", "财政", "货币制度", "纸币", "银", "交子", "会子", "边疆"],
    "world_trade": ["世界贸易", "国际贸易", "港口", "航线", "商路", "跨区域", "商人", "外交", "制度比较"],
    "belt_road": ["一带一路", "跨境", "结算", "港口", "供应链", "丝绸之路", "外交", "基础设施", "通道治理", "制度类比"],
}

GENERIC_QUERY_TERMS = {
    "历史",
    "证据",
    "资料",
    "制度",
    "治理",
    "近代",
    "上海",
    "影响",
    "作用",
    "联系",
    "关系",
    "相关",
    "什么",
    "哪些",
    "如何",
    "问题",
}
GENERIC_TITLE_MARKERS = ["出版社", "书店", "编辑部", "出版部", "展览会"]


def retrieve(question: str, top_k: int = 6, mode: str = "general", require_open_source: bool = True) -> list[RetrievalResult]:
    records = [record for record in load_records() if not require_open_source or is_openable_uri(record.source_uri)]
    query_terms = expand_query_terms(question, mode=mode)
    anchor_terms = required_anchor_terms(question, records)
    scored: list[RetrievalResult] = []
    for record in records:
        text = record_text(record)
        matched = [term for term in query_terms if term and term.lower() in text]
        score = score_record(record, question, query_terms, matched)
        if anchor_terms and not any(term.lower() in text for term in anchor_terms):
            score -= 22.0
        if score > 0:
            scored.append(RetrievalResult(record=record, score=score, matched_terms=matched[:8]))
    scored.sort(key=lambda x: (x.score, matched_title_hit_count(x), source_quality_rank(x.record), x.record.is_live_api), reverse=True)
    return diversify_results(scored, question, query_terms, top_k=top_k, anchor_terms=anchor_terms)


def expand_query_terms(question: str, mode: str = "general") -> list[str]:
    base = [
        t
        for t in re.split(r"[\s,，。！？；;:/\\-]+", question.lower())
        if 2 <= len(t) <= 32 and t not in GENERIC_QUERY_TERMS
    ]
    chars = []
    for term in DOMAIN_TERMS.values():
        chars.extend(term)
    selected = []
    for label, terms in DOMAIN_TERMS.items():
        if any(t.lower() in question.lower() for t in terms + [label]):
            selected.extend(terms)
    # Add common Chinese substrings manually because whitespace tokenization is weak for Chinese.
    for token in chars:
        if token in question or token.lower() in question.lower():
            selected.append(token)
    mode_terms = MODE_TERMS.get(mode, MODE_TERMS["general"])
    return unique(base + direct_question_tokens(question) + selected + mode_terms + ["历史", "证据"])


def score_record(record: EvidenceRecord, question: str, query_terms: list[str], matched: list[str]) -> float:
    if not matched:
        return 0.0
    question_lower = question.lower()
    direct_matches = [term for term in set(matched) if term.lower() in question_lower]
    mode_matches = [term for term in set(matched) if term.lower() not in question_lower]
    direct_terms = direct_query_terms(question, query_terms)
    specific_direct_matches = [term for term in direct_terms if term.lower() in record_text(record)]
    score = float(len(direct_matches)) * 4.2 + float(len(mode_matches)) * 0.9
    score += float(len(specific_direct_matches)) * 2.6
    title = record.title.lower()
    topics = " ".join(record.topics).lower()
    for term in set(matched):
        t = term.lower()
        if t in title:
            score += 4.0 if t in question_lower else 1.4
        if t in topics and t in (record.title + record.snippet).lower():
            score += 2.6 if t in question_lower else 1.0
    for token in direct_question_tokens(question):
        if token in title:
            score += 2.5
        elif token in record_text(record):
            score += 1.2
    if record.is_live_api:
        score += 4.0
    score += source_quality_score(record)
    if direct_terms and not specific_direct_matches:
        score -= 7.0
    if is_generic_record(record) and len(specific_direct_matches) < 2:
        score -= 9.0
    if "稳定" in question and any(t in record_text(record) for t in ["纸币", "信用", "结算", "货币"]):
        score += 2.0
    if "一带一路" in question and any(t in record_text(record) for t in ["丝绸之路", "商路", "港口", "外交"]):
        score += 2.0
    return score


def direct_query_terms(question: str, query_terms: list[str]) -> list[str]:
    question_lower = question.lower()
    direct = []
    for term in query_terms:
        cleaned = str(term or "").strip()
        if not cleaned or cleaned in GENERIC_QUERY_TERMS:
            continue
        if len(cleaned) > 24:
            continue
        if cleaned.lower() in question_lower:
            direct.append(cleaned)
    return unique(direct)


def diversify_results(
    scored: list[RetrievalResult],
    question: str,
    query_terms: list[str],
    *,
    top_k: int,
    anchor_terms: list[str] | None = None,
) -> list[RetrievalResult]:
    if not scored:
        return []
    direct_terms = direct_query_terms(question, query_terms)
    anchor_terms = anchor_terms or []
    direct_pool = [
        result for result in scored
        if has_specific_direct_match(result.record, direct_terms)
        and (not anchor_terms or any(term.lower() in record_text(result.record) for term in anchor_terms))
    ]
    context_pool = [result for result in scored if result not in direct_pool]
    if direct_terms and len(direct_pool) >= min(2, top_k):
        context_limit = min(2, max(0, top_k - len(direct_pool)))
        pool = direct_pool + context_pool[:context_limit]
    else:
        pool = scored
    pool = prioritize_specific_sources(pool)

    selected: list[RetrievalResult] = []
    duplicate_later: list[RetrievalResult] = []
    weak_later: list[RetrievalResult] = []
    seen_keys: set[str] = set()
    for result in pool:
        duplicate_key = normalized_record_key(result.record)
        if duplicate_key in seen_keys:
            duplicate_later.append(result)
            continue
        if is_weak_context_result(result, direct_terms) and len(selected) < min(3, top_k):
            weak_later.append(result)
            continue
        selected.append(result)
        seen_keys.add(duplicate_key)
        if len(selected) >= top_k:
            return selected[:top_k]

    for result in weak_later + duplicate_later:
        duplicate_key = normalized_record_key(result.record)
        if duplicate_key in seen_keys and len(selected) >= max(1, top_k - 1):
            continue
        selected.append(result)
        seen_keys.add(duplicate_key)
        if len(selected) >= top_k:
            break
    return selected[:top_k]


def prioritize_specific_sources(results: list[RetrievalResult]) -> list[RetrievalResult]:
    if not results:
        return []
    best_score = max(result.score for result in results)
    threshold = best_score * 0.55
    preferred = [
        result
        for result in results
        if source_quality_rank(result.record) >= 2 and result.score >= threshold
    ]
    preferred_ids = {id(result) for result in preferred}
    rest = [result for result in results if id(result) not in preferred_ids]
    preferred.sort(key=lambda result: (source_quality_rank(result.record), result.score, result.record.is_live_api), reverse=True)
    return preferred + rest


def has_specific_direct_match(record: EvidenceRecord, direct_terms: list[str]) -> bool:
    if not direct_terms:
        return True
    text = record_text(record)
    return any(term.lower() in text for term in direct_terms)


def is_weak_context_result(result: RetrievalResult, direct_terms: list[str]) -> bool:
    if not direct_terms:
        return False
    specific_direct_matches = [term for term in direct_terms if term.lower() in record_text(result.record)]
    return not specific_direct_matches or (is_generic_record(result.record) and len(specific_direct_matches) < 2)


def is_generic_record(record: EvidenceRecord) -> bool:
    title = record.title
    topics = " ".join(record.topics)
    if any(marker in title for marker in GENERIC_TITLE_MARKERS):
        return True
    return any(marker in topics for marker in ["shanghai_yearbook_org"]) and any(marker in title for marker in ["出版社", "书店"])


def source_quality_rank(record: EvidenceRecord) -> int:
    uri = str(record.source_uri or "").strip().lower()
    if "data.library.sh.cn/entity/" in uri:
        return 3
    if uri.startswith("shlib-api://"):
        return 2
    if uri.startswith(("http://", "https://")) and "www.library.sh.cn/resource?type=" not in uri:
        return 2
    if record.is_live_api:
        return 1
    return 0


def source_quality_score(record: EvidenceRecord) -> float:
    rank = source_quality_rank(record)
    if rank >= 3:
        return 10.0
    if rank == 2:
        return 6.0
    if rank == 1:
        return 2.0
    return -8.0


def matched_title_hit_count(result: RetrievalResult) -> int:
    title = str(result.record.title or "").lower()
    return sum(1 for term in result.matched_terms if term and term.lower() in title)


def normalized_record_key(record: EvidenceRecord) -> str:
    title = re.sub(r"@\w+|[；;|｜].*$", "", record.title).strip().lower()
    title = re.sub(r"\s+", "", title)
    if title:
        return title
    return str(record.source_uri or record.record_id).strip().lower()


def direct_question_tokens(question: str) -> list[str]:
    tokens = [t for t in re.split(r"[\s,，。！？；;:/\\-]+", question.lower()) if 2 <= len(t) <= 24]
    chinese = []
    for candidate in re.findall(r"[\u4e00-\u9fff]{2,8}", question):
        if any(marker in candidate for marker in ["什么", "哪些", "如何", "怎样", "怎么", "是否", "可以", "为什么", "有什么"]):
            continue
        if candidate.startswith(("变", "改", "撑", "支撑", "处理", "影响", "改变")):
            continue
        if len(candidate) > 6:
            continue
        if candidate not in {"历史", "今天", "目前", "现在", "研究问题"}:
            chinese.append(candidate)
    place_tokens = re.findall(r"[\u4e00-\u9fff]{2,6}(?:路|街|道|弄|里|坊|滩)", question)
    return unique(tokens + chinese + place_tokens)


def required_anchor_terms(question: str, records: list[EvidenceRecord]) -> list[str]:
    """Find person/place entities explicitly present in the question.

    These anchors prevent generic words such as “上海” or “联系” from filling a
    person-specific answer with unrelated records.
    """
    candidates: list[str] = []
    candidates.extend(re.findall(r"[\u4e00-\u9fff]{2,6}(?:路|街|道|弄|里|坊|滩)", question))
    for record in records:
        for value in record.persons + record.places:
            cleaned = str(value or "").strip()
            if 2 <= len(cleaned) <= 12 and cleaned not in GENERIC_QUERY_TERMS and cleaned in question:
                candidates.append(cleaned)
    for known in ["盛宣怀", "鲁迅", "张骞", "张爱玲", "宋庆龄", "霞飞路", "南京路", "外滩", "武康路"]:
        if known in question:
            candidates.append(known)
    return unique(candidates)


def record_text(record: EvidenceRecord) -> str:
    return " ".join(
        [
            record.title,
            record.snippet,
            record.date,
            " ".join(record.persons),
            " ".join(record.places),
            " ".join(record.topics),
            record.evidence_type,
            record.provenance_note,
            " ".join(record.public_tags),
            " ".join(record.verification_notes),
            record.dataset,
        ]
    ).lower()


def is_openable_uri(uri: str) -> bool:
    value = str(uri or "").strip().lower()
    return value.startswith(("http://", "https://", "shlib-api://"))


def unique(values: list[str]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        v = value.strip()
        if not v or v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out
