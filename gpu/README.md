# ContextLens GPU experiment

This directory contains the reproducible offline GPU task funded through the
DKU Library RunPod budget. It creates bilingual semantic representations for
the nine published street dossiers, evaluates 30 Chinese, English, and
cross-language retrieval questions, and exports a deterministic related-street
graph for the website.

The GPU pipeline does not generate historical claims and is not required at
website runtime.

```bash
bash gpu/run_contextlens_gpu.sh
```

Expected outputs:

- `data/processed/gpu_corpus_manifest.json`
- `data/processed/gpu_related_streets.json`
- `reports/gpu/retrieval_results.json`
- `reports/gpu/runpod_run_manifest.json`
