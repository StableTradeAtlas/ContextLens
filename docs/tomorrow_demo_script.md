# ContextLens Demo Script

## One-Line Start

```bash
cd "/Users/oushilin/Desktop/SRS/02_Shanghai_Library_Project/StableTrade_Atlas_ODC-main" && python3 start.py
```

This prepares the local evidence index, starts the web server, and opens the browser. If the app is already running, the command opens the existing local site.

## 30-Second Positioning

文脉镜 ContextLens is a verifiable historical-discovery agent for Shanghai Library open data.

It does not merely let AI tell history. It shows how a person, place, event, document, or old address can be rebuilt into a traceable historical dossier with entity links, a claim-level evidence ledger, counter-evidence notes, investigation replay, and a data-use receipt.

## What Is Working Now

- Local bilingual web MVP at `http://127.0.0.1:8765`
- First screen asks: **你想追寻哪条历史线索？**
- Public task modes: 追一个人, 寻一处地, 还原一件事, 读懂一份文献
- Public expansion modes: 城市记忆漫游, 家族线索寻踪
- Preserved flagship collection: 上海与世界专题
- Historical Evidence Compiler output
- Source passport: evidence type, provenance note, public tags, geo-review status, and verification notes
- Award readiness panel: public reuse, Library data use, traceability, investigation depth, guardrails, and differentiation
- Professional research-design panel: research design, data strategy, evidence protocol, public productization, submission risks, and curatorial pitch
- Larger local demo pool: 54 transparent seed records and default 10-card retrieval
- Target dossier output: one-line finding, clickable historical timeline, relationship network, spatial trace, evidence cards, gaps, follow-up routes, story mode, and research mode
- Evidence quality gates: provenance, source diversity, counter-evidence, live-data replacement, and spatial precision
- Claim-level evidence ledger
- Counter-evidence and gap audit
- Investigation replay
- Data-use receipt
- Dynamic claim-evidence graph
- Evidence sandbox for toggling source cards
- Clickable evidence cards and source detail pages

## Main Demo Flow

1. Run the one-line start command.

2. Start with a public-facing clue:

```text
南京路的百货公司、报刊广告和市民生活可以串成怎样的城市记忆路线？
```

Recommended controls:

- Language: 中文
- Investigation task: 城市记忆漫游
- Output style: 历史调查档案
- Evidence count: 6

3. Then use the flagship research clue:

```text
盛宣怀与上海的铁路、银行和航运有什么联系？
```

Recommended controls:

- Language: 中文
- Investigation task: 追一个人
- Output style: 历史调查档案
- Evidence count: 6

4. Explain the output:

- 一句话发现 gives the public-facing conclusion.
- 评审就绪度 summarizes whether the run is strong on public reuse, Library data use, traceability, investigation depth, guardrails, and differentiation.
- 专业研究设计 explains the research design, data strategy, evidence protocol, public productization, submission risk, and curatorial pitch.
- 历史时间线 turns records into clickable event nodes.
- 人物关系网 shows people, institutions, places, documents, and sources connected by evidence.
- 空间轨迹 lists historical places and clearly marks modern coordinates as requiring gazetteer/geocoding verification.
- 故事模式 gives a public-facing narrative while preserving evidence boundaries.
- 研究模式 gives the method, citation protocol, and review notes.
- 证据质量闸门 shows whether provenance, source diversity, counter-evidence, live replacement, and spatial precision are ready.
- 实体链接 shows people, places, organizations, events, documents, and concepts.
- 主张级证据台账 shows which claim is direct support, context support, weak support, or needs more evidence.
- 反证与空白 makes uncertainty visible instead of hiding it.
- 证据沙盒 lets the user temporarily remove source cards and see which claims become weaker.
- 调查回放 shows how the agent moved from clue to dossier.
- 数据使用收据 makes open-data use visible to judges.
- 来源护照 makes each evidence card auditable: evidence type, provenance, time span, public tags, and verification notes.

5. Show the dynamic claim-evidence graph:

- Clue, entities, sources, claims, and dossier are connected.
- Source nodes open evidence links or local source detail pages.

6. Show the 3D investigation protocol:

```text
Clue -> Plan -> Search -> Entity Link -> Evidence Graph -> Claim Ledger -> Counter-Evidence Audit
```

## Backup CLI Demo

```bash
python3 scripts/demo_query.py "如果我只知道家谱中的一个姓名和上海旧地址，下一步该查哪些证据？" --language zh --mode family_memory --output-style investigation_dossier
```

## What To Say Honestly

The MVP is not yet a full production digital-humanities platform. It currently uses a lightweight SQLite evidence store, deterministic retrieval, transparent seed fallback, and local claim-audit logic.

The industrialization path is:

1. Add more official dataset-specific tools.
2. Strengthen entity disambiguation and alias tables.
3. Add date parsing and contradiction detection.
4. Add historical gazetteer/geocoding for precise map coordinates.
5. Add claim-citation precision evaluation.
6. Deploy with uptime monitoring and logs before submission.
