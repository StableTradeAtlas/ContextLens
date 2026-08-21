# ContextLens Architecture

```text
Historical clue
    ↓
Clue parsing and task selection
    ↓
Investigation plan
    ↓
Shanghai Library retrieval tools + local SQLite evidence store
    ↓
EvidenceRecord normalization
    ↓
Source-passport metadata
    ↓
Entity linking
    ↓
Claim-level evidence ledger
    ↓
Counter-evidence and gap audit
    ↓
Professional research-design briefing
    ↓
Replayable historical dossier
```

## Product Frame

ContextLens is designed around four public tasks:

- 追一个人
- 寻一处地
- 还原一件事
- 读懂一份文献

The current build also includes two public-expansion modes:

- 城市记忆漫游: old addresses, streets, buildings, maps, photos, public culture, and walkable dossiers.
- 家族线索寻踪: surnames, genealogies, alumni lists, old residences, relatives, and personal memory.

The original StableTrade Atlas topic now lives inside **上海与世界专题**. It remains useful for monetary history, ports, customs, merchants, banks, shipping, Silk Road, and Belt and Road analogy demos, but it no longer defines the whole product.

## Historical Evidence Compiler

The backend keeps the existing deterministic retrieval foundation and adds an investigation dossier to every answer:

```text
question_analysis
    ↓
entities
    ↓
plan
    ↓
claims
    ↓
counter_evidence
    ↓
receipt
    ↓
graph + replay
```

The key rule is: **no important claim should appear without evidence status**. The current implementation labels each claim as direct support, context support, weak support, or needs more evidence.

Every evidence card also carries a source passport: evidence type, provenance note, time span, public tags, geo status, and verification notes. This makes demo seed records visibly different from live API records and gives reviewers a clear manual-review route.

## Award Readiness Layer

Every answer includes an `award_readiness` object. It scores:

- public reusability;
- Shanghai Library data utilization;
- claim-level traceability;
- investigation depth;
- guardrails and audit;
- differentiation from generic RAG.

This is not a substitute for judging; it is an internal quality cockpit for first-prize-oriented iteration.

## Professional Briefing Layer

Every answer also includes `professional_briefing`, a compact method section for proposal and demo use:

- research design;
- data strategy;
- evidence protocol;
- public productization;
- submission risks;
- curatorial pitch.

The web UI places this near the top of the result page so reviewers see the logic of the investigation before reading the detailed modules.

## Data Flow

```text
Shanghai Library API key
    ↓
app.library_client
    ↓
raw JSON cache under data/raw/
    ↓
normalized EvidenceRecord objects
    ↓
SQLite local store
    ↓
retrieval + evidence fit scoring
    ↓
investigation dossier + UI
```

If the live API is unavailable, the demo loads transparent seed records from `app/sample_data.py`.

The local demo seed pool currently contains 54 transparent records across people, places, events, documents, maps, images, genealogies, periodicals, institutions, mobility, public culture, and urban daily life. The health endpoint exposes a data-catalog summary so the UI can show dataset families, evidence types, and public-use tags.

## Visual Layers

The web demo has two canvas visualizations:

- 3D investigation protocol atlas: shows the product's Plan -> Search -> Link -> Claim -> Audit workflow.
- Per-answer claim-evidence graph: shows the current clue, linked entities, evidence sources, audited claims, and final dossier.

Both are local canvas renderers and do not depend on an external CDN.

## Security Principles

- API key is loaded from `.env` or environment variables only.
- The browser frontend never receives the API key.
- Raw data and logs are gitignored by default.
- User clues are length-limited in the local web MVP.
- Dynamic frontend rendering escapes HTML.
- User input is never executed as a shell command.
- Public answers must include citations or be marked for review.
- Finance/payment questions receive a non-financial-advice compliance warning.
