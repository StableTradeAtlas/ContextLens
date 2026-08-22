<div align="center">

# 文脉镜 ContextLens

### Shanghai Street History Archive · 上海街道历史档案

Choose a completed Shanghai street dossier and follow its names, people,
buildings, events, images, maps, and sources in one bilingual historical route.

</div>

---

## Product

ContextLens turns fragmented street records into readable, verifiable public
history. The public interface deliberately uses a **curated catalogue**, not an
unrestricted search box: every listed street must complete the full experience
without an empty chapter, undated timeline item, broken primary action, or
unsupported claim.

The current catalogue contains nine bilingual dossiers:

| Street dossier | District | Coverage |
|---|---|---|
| 霞飞路 / 淮海中路 · Avenue Joffre / Huaihai Middle Road | Huangpu / Xuhui | 1901–present |
| 衡山路 · Hengshan Road | Xuhui | 1920–present |
| 重庆南路 · South Chongqing Road | Huangpu | 1923–present |
| 陕西南路 · South Shaanxi Road | Huangpu / Xuhui | 1920–present |
| 南京西路 · West Nanjing Road | Huangpu / Jing'an | 1932–present |
| 多伦路 · Duolun Road | Hongkou | 1911–present |
| 四川北路 · North Sichuan Road | Hongkou | 1925–present |
| 长阳路 · Changyang Road | Hongkou / Yangpu | 1903–present |
| 外滩 / 中山东一路 · The Bund / East Zhongshan No. 1 Road | Huangpu | 1869–present |

Each dossier provides:

1. A concise editorial overview in Chinese and English.
2. A verified historical-name sequence when available.
3. Dated street events, buildings, institutions, and people.
4. Rights-aware photographs and maps with item-specific explanations.
5. Contemporary geographic orientation without false historical precision.
6. Readable source entries connected to the relevant narrative.
7. A printable reader edition.

## Evidence and data

Shanghai Library open data is the historical evidence core. The packaged,
credential-free snapshot contains **154 official records** across road and
place-name entities, historical events, historic buildings, people, and
institutions.

Traceable auxiliary collections add visual and spatial context:

- Shanghai municipal and district gazetteers and public heritage records
- Virtual Shanghai
- Wikimedia Commons
- Princeton University Library historical maps
- Library of Congress collections
- OpenStreetMap / OpenFreeMap for present-day orientation

Official historical evidence and contextual visual material remain distinct.
Every displayable image records its provider, creator, licence, attribution,
source page, and role in the dossier.

## Publication gate

A street appears in the public catalogue only when:

- its identity is unambiguous;
- its chronology contains meaningful, dated material;
- its displayed claims have supporting records;
- its required chapters contain useful content;
- its visual material has usable rights and attribution metadata;
- its internal and external actions have a working destination or fallback;
- its complete route passes data, interaction, and presentation checks.

Incomplete resolver candidates remain internal and are not presented as
finished histories.

## Quick start

Requirements: Python 3.10 or newer. The packaged experience does not require a
Shanghai Library API key, model key, or Node.js.

```bash
git clone https://github.com/StableTradeAtlas/ContextLens.git
cd ContextLens
./start-contextlens
```

Open <http://127.0.0.1:8765>. To choose another port:

```bash
CONTEXTLENS_PORT=8777 ./start-contextlens
```

Platform launchers are also included:

- macOS: `START_HERE_MAC.command`
- Windows: `START_HERE_WINDOWS.bat`
- Linux: `START_HERE_LINUX.sh`

## Frontend development

Node.js is needed only when modifying the frontend:

```bash
npm ci
npm run check
npm run build
```

## Architecture

```text
ContextLens/
├── frontend/src/                 # Bilingual catalogue and street dossier UI
├── app/
│   ├── catalog.py                # Public publication manifest
│   ├── media_registry.py         # Rights-aware visual registry
│   ├── place_investigation.py    # Resolution and dossier pipeline
│   ├── official_snapshot.py      # Shanghai Library snapshot builder
│   ├── historical_maps.py        # Map catalogue and precision boundaries
│   ├── storage.py                # Evidence index
│   └── memory_web.py             # Local HTTP application and API
├── data/processed/
│   └── shlibrary_official_snapshot.json
├── tests/                        # Publication, evidence, media, and regressions
└── start.py
```

Primary API endpoints:

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/catalog` | Return the curated public street catalogue |
| `GET` | `/api/health` | Report packaged evidence coverage and health |
| `POST` | `/api/place/resolve` | Resolve the catalogue street identity |
| `POST` | `/api/investigations` | Build an evidence-bound street dossier |
| `GET` | `/api/investigations/{id}` | Return progress or the completed dossier |

## Validation

```bash
npm run check
npm run build
python3 tests/test_catalog_publication.py
PYTHONPATH=. python3 tests/test_media_registry.py
python3 tests/test_place_investigation.py
python3 tests/test_agent.py
```

The publication suite checks all nine catalogue routes for complete identity
resolution, dated chronology, required source coverage, visual metadata, and
valid bilingual content. The core experience remains deterministic and works
without an LLM.

## Optional live development

For authorized development against live services, copy `.env.example` to
`.env` and configure credentials locally. `.env`, API caches, logs, and local
runtime data are excluded from Git. API keys must never enter frontend bundles,
source URLs, screenshots, or audit logs.

## Competition proposition

> Search is easy. Historical traceability is the product.

ContextLens gives visitors a designed way to read how a Shanghai street changed
and to open the material behind that account. It is public history that can be
examined and reused—not an automatically generated anecdote.

---

<div align="center">

**文脉镜 ContextLens · Shanghai Street History Archive**

</div>
