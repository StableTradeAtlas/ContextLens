# Data Card / Datasheet Draft

## Dataset Purpose

This MVP uses a local evidence store to prototype the ContextLens historical investigation workflow. The intended production data source is Shanghai Library official open data accessed through the competition API key. If the live API is unavailable, transparent demo seed records keep the local presentation usable.

## Sources

- Primary intended source: Shanghai Library Open Data API.
- Current fallback source: transparent demo seed records in `app/sample_data.py`.

## Fields

- `record_id`
- `title`
- `snippet`
- `source`
- `source_uri`
- `dataset`
- `date`
- `persons`
- `places`
- `topics`
- `evidence_type`
- `provenance_note`
- `time_span`
- `geo`
- `public_tags`
- `verification_notes`
- `is_live_api`
- retrieval score and matched terms are computed at query time

## Demo Seed Coverage

The transparent seed set currently contains 54 records. It covers both the original Shanghai-and-world trade topic and public-facing use cases:

- city-memory walks from old addresses, roads, buildings, old maps, and old photos;
- family-memory tracing from genealogy, names, alumni lists, and old residences;
- document-detective workflows for rare books, periodicals, archives, title records, seals, and inscriptions;
- public-culture dossiers around writers, film, publishing, public life, and community exhibits.
- mobility, education, healthcare, parks, exhibitions, labor history, transport, visual culture, directories, oral history, and urban governance.

## Limitations

- Demo seed records are not a substitute for official API retrieval.
- Source-passport metadata helps route review, but it does not itself certify historical truth.
- External submission should re-run live API ingestion and manually review citations.
- The prototype is educational and does not provide financial, legal, trading, regulatory, or payment-implementation advice.
- The MVP builds a retrieval/audit layer. It does not fine-tune a model in v0.1.
