# Similar-Project Scan and Positioning

Research date: 2026-08-02

## Summary

There are already many projects around AI + historical data + RAG + knowledge graphs. ContextLens should not claim novelty from those ingredients alone.

The defensible position is:

> Turn historical QA into a replayable, inspectable, and challengeable evidence investigation.

In product terms, the user should feel: "I gave the system one clue, and it showed me how it rebuilt the historical context from library evidence."

In technical terms, the core is a **claim-level provenance-aware historical investigation agent**:

```text
Clue -> Plan -> Search -> Normalize -> Entity Link
-> Claim Ledger -> Counter-Evidence -> Audit -> Dossier
```

## Official Fit

The 2026 Shanghai Library Open Data Competition announcement says the application and agent track may take many forms, including websites, mobile web apps, mini programs, agents, and apps. It also requires official competition datasets as the basis of creation.

The strongest fit is direction 2, "在时空经纬中探寻人物与历史", because it explicitly asks for integration of biography, historical places, historical events, associated narratives, knowledge graphs, spatiotemporal visualization, digital portraits, AI narrative generation, and historical exploration.

Source: [第十一届上海图书馆开放数据竞赛公告](https://www.library.sh.cn/article/95854)

Shanghai Library's digital humanities data ecosystem includes people, places, time, events, objects, genealogies, archives, manuscripts, ancient books, maps, and ontology vocabulary.

Source: [Digital Humanities Platform of Shanghai Library](https://library.shanghai.nyu.edu/datasets/digital-humanities-platform-shanghai-librarylishirenwendashujupingtai)

## Similar Projects

### Shanghai Library competition ecosystem

- **今秘阁**: An artwork/IIIF-centered agent for zooming, version comparison, OCR, and guided interpretation. It is tool-rich around cultural objects.
- **CBDBChat**: A multi-agent RAG system over CBDB with Text2Cypher, retrievers, routing, and knowledge-graph querying for historical persons.
- **频段1931**: Uses knowledge graphs, historical maps, 3D modeling, and multi-role dialogue for immersive historical memory.

Source: [CBDB Shanghai Library Open Data Competition page](https://chinesecbdb.hsites.harvard.edu/shanghaitushuguankaifangshujujingsai)

### International digital-humanities infrastructure

- **Pelagios Network / Recogito**: Community and tools for linked open historical data, semantic annotation of texts/images, and tagging people, places, and events.
- **World Historical Gazetteer**: Open linked historical place data with more than 2 million place records, dataset linking, map/time-slider exploration, and a principle that places can have multiple historical names and characteristics.
- **ResearchSpace / CIDOC CRM**: Cultural heritage research environment based on semantic web and knowledge representation, focused on integrating heterogeneous data without losing meaning or perspective.
- **Linked Art**: A cultural heritage data model built around shared patterns for artworks, people, places, events, documents, and assertions.

Sources:

- [Pelagios Network](https://pelagios.org/)
- [Recogito](https://recogito.pelagios.org/)
- [World Historical Gazetteer overview](https://pleiades.stoa.org/news/blog/world-historical-gazetteer)
- [ResearchSpace on CIDOC CRM](https://cidoc-crm.org/Resources/researchspace)
- [Linked Art model](https://linked.art/model/)

### Current AI/RAG research adjacency

- A 2026 historical GraphRAG paper shows that agentic retrieval over noisy historical knowledge graphs is an active research direction, especially when archival records contain OCR and transcription noise.
- A 2026 survey on evidence tracing and execution provenance argues that trustworthy agents need traceable connections among retrieved evidence, tool outputs, intermediate claims, actions, and final answers.

Sources:

- [Robust Interpretation of Historical Documents in Knowledge Graphs Through Query Inference and Execution](https://arxiv.org/abs/2607.24475)
- [From Agent Traces to Trust: A Survey of Evidence Tracing and Execution Provenance in LLM Agents](https://arxiv.org/html/2606.04990v4)

## What To Avoid

- Do not say the novelty is simply "AI + RAG + knowledge graph".
- Do not center the product on stablecoins, trading, investment, or blockchain.
- Do not make the visualization only a technical pipeline.
- Do not attach citations only to the whole answer; claim-level support is stronger.
- Do not hide weak support or missing evidence.

## Differentiation

ContextLens should emphasize five working capabilities:

- Query planner: turns one vague clue into investigation tasks.
- Cross-dataset entity linker: connects people, places, institutions, events, documents, aliases, and topics.
- Claim-evidence graph: binds each important claim to evidence records and support strength.
- Counter-evidence auditor: surfaces weak support, missing terms, date uncertainty, and demo/live data boundaries.
- Investigation replay: shows how the system got from clue to dossier.

## Product Implication

The first screen should ask:

> 你想追寻哪条历史线索？

The four public tasks are:

- 追一个人
- 寻一处地
- 还原一件事
- 读懂一份文献

The original StableTrade direction becomes:

> 上海与世界专题：货币、口岸、商人和全球贸易

## Current Implementation Status

Implemented in this MVP:

- New ContextLens product framing.
- Public investigation modes.
- `investigation` JSON returned by `answer_question`.
- Entity link extraction.
- Claim-level evidence ledger.
- Counter-evidence and gap report.
- Data-use receipt.
- Investigation replay.
- Dynamic claim-evidence graph in the web demo.
- Evidence sandbox toggles in the UI.

Next industrialization steps:

- Add more official dataset-specific tool adapters.
- Add persistent entity IDs and alias tables.
- Add stronger date parsing and contradiction detection.
- Add evaluation metrics for entity-linking accuracy and claim citation precision.
- Add deployment, logs, observability, and uptime checks before submission.
