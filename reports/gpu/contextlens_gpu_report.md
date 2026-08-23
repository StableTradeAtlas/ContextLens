# ContextLens RunPod GPU experiment

## Purpose

DKU Library funding supported a small, reproducible GPU-assisted bilingual
retrieval experiment for ContextLens. The computation generated semantic
relationships among the nine reviewed street dossiers and evaluated whether
Chinese, English, and mixed-language questions retrieve the intended street.

The GPU did not write historical claims. The public site consumes only the
precomputed related-street graph and continues to bind historical statements to
reviewed source records.

## Recorded environment

| Field | Recorded value |
|---|---|
| Provider | RunPod |
| GPU | NVIDIA RTX PRO 6000 Blackwell Server Edition |
| GPU memory | 94.97 GB |
| CUDA | 12.8 |
| PyTorch | 2.8.0+cu128 |
| Model | BAAI/bge-m3 |
| Model revision | `5617a9f61b028005a4858fdac845db406aefb181` |
| Source Git commit | `f1796f870b2e3bdcb872ee130ee1a42204c691dc` |
| Street documents | 9 |
| Evaluation queries | 30 |
| Benchmark repetitions | 10 |
| Peak allocated GPU memory | 5,052.98 MB |
| Measured model-run duration | 13.817 seconds |
| Configured RunPod rate | $2.10/hour |
| Estimated measured compute cost | $0.0081 |

The estimated cost covers the recorded Python process duration, not Pod setup,
package download, idle time, storage, or the account invoice. RunPod billing
records remain the authoritative source for the actual charge.

## Retrieval results

| Evaluation group | Recall@1 | Recall@3 | MRR |
|---|---:|---:|---:|
| All 30 questions | 0.70 | 0.90 | 0.8173 |
| Chinese | 0.70 | 0.90 | 0.8250 |
| English | 0.50 | 0.80 | 0.6768 |
| Chinese–English mixed | 0.90 | 1.00 | 0.9500 |

These results are reported without adjustment. They demonstrate useful
cross-language retrieval while also showing that English-only retrieval has
room for improvement. The related-street graph is therefore restricted to the
nine already reviewed dossiers and is presented as discovery guidance, not
historical evidence.

## Reproduction

```bash
bash gpu/run_contextlens_gpu.sh
```

Machine-readable outputs:

- `reports/gpu/runpod_run_manifest.json`
- `reports/gpu/retrieval_results.json`
- `data/processed/gpu_corpus_manifest.json`
- `data/processed/gpu_related_streets.json`
