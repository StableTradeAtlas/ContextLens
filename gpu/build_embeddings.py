#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parents[1]
MODEL = os.environ.get("CONTEXTLENS_EMBEDDING_MODEL", "BAAI/bge-m3")
BATCH_SIZE = int(os.environ.get("CONTEXTLENS_GPU_BATCH_SIZE", "16"))
REPEATS = int(os.environ.get("CONTEXTLENS_GPU_REPEATS", "10"))


def git_value(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def rank_metrics(results: list[dict]) -> dict:
    reciprocal = []
    hit1 = hit3 = 0
    by_language: dict[str, list[int]] = {}
    for result in results:
        rank = result["expected_rank"]
        reciprocal.append(1 / rank if rank else 0)
        hit1 += int(rank == 1)
        hit3 += int(rank is not None and rank <= 3)
        by_language.setdefault(result["language"], []).append(rank or 0)
    n = len(results)
    return {
        "query_count": n, "recall_at_1": hit1 / n, "recall_at_3": hit3 / n,
        "mean_reciprocal_rank": sum(reciprocal) / n,
        "by_language": {
            language: {
                "query_count": len(ranks),
                "recall_at_1": sum(rank == 1 for rank in ranks) / len(ranks),
                "recall_at_3": sum(0 < rank <= 3 for rank in ranks) / len(ranks),
                "mean_reciprocal_rank": sum(1 / rank for rank in ranks if rank) / len(ranks),
            } for language, ranks in by_language.items()
        },
    }


def main() -> None:
    if not torch.cuda.is_available():
        raise SystemExit("CUDA GPU is required for this recorded experiment")
    started_at = datetime.now(timezone.utc)
    started = time.perf_counter()
    corpus = json.loads((ROOT / "data/processed/gpu_corpus_manifest.json").read_text())
    documents = corpus["documents"]
    queries = corpus["evaluation_queries"]
    model_load_started = time.perf_counter()
    model = SentenceTransformer(MODEL, device="cuda")
    model_load_seconds = time.perf_counter() - model_load_started
    encode_options = dict(batch_size=BATCH_SIZE, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
    model.encode(["ContextLens GPU warm-up / 文脉镜 GPU 预热"], **encode_options)
    torch.cuda.synchronize()
    encode_started = time.perf_counter()
    document_vectors = None
    for _ in range(REPEATS):
        document_vectors = model.encode([item["text"] for item in documents], **encode_options)
    torch.cuda.synchronize()
    encode_seconds = time.perf_counter() - encode_started
    query_vectors = model.encode([item["query"] for item in queries], **encode_options)
    similarities = np.matmul(query_vectors, document_vectors.T)
    results = []
    street_ids = [item["street_id"] for item in documents]
    for query, scores in zip(queries, similarities):
        order = np.argsort(-scores)
        ranking = [{"street_id": street_ids[int(index)], "score": round(float(scores[index]), 6)} for index in order]
        expected_rank = next((i + 1 for i, item in enumerate(ranking) if item["street_id"] in query["expected"]), None)
        results.append({**query, "expected_rank": expected_rank, "ranking": ranking})
    metrics = rank_metrics(results)
    street_similarity = np.matmul(document_vectors, document_vectors.T)
    related = {}
    for i, document in enumerate(documents):
        order = [int(index) for index in np.argsort(-street_similarity[i]) if int(index) != i][:3]
        entries = []
        for index in order:
            other = documents[index]
            shared_zh = sorted(set(document["themes_zh"]) & set(other["themes_zh"]))
            shared_en = sorted(set(document["themes_en"]) & set(other["themes_en"]))
            entries.append({
                "street_id": other["street_id"], "score": round(float(street_similarity[i, index]), 6),
                "reason_zh": "共同主题：" + "、".join(shared_zh) if shared_zh else "双语档案内容具有语义关联",
                "reason_en": "Shared themes: " + ", ".join(shared_en) if shared_en else "Semantically related bilingual dossier content",
            })
        related[document["street_id"]] = entries
    finished_at = datetime.now(timezone.utc)
    duration = time.perf_counter() - started
    rate = float(os.environ.get("RUNPOD_RATE_USD_PER_HOUR", "0") or 0)
    props = torch.cuda.get_device_properties(0)
    try:
        model_revision = model._first_module().auto_model.config._commit_hash
    except Exception:
        model_revision = None
    run_manifest = {
        "schema_version": "1.0", "purpose": "ContextLens bilingual street-evidence indexing and retrieval evaluation",
        "started_at": started_at.isoformat(), "finished_at": finished_at.isoformat(), "duration_seconds": round(duration, 3),
        "pod_id": os.environ.get("RUNPOD_POD_ID") or os.environ.get("HOSTNAME"),
        "git_commit": git_value("rev-parse", "HEAD"), "git_status_clean": not bool(git_value("status", "--porcelain")),
        "model": MODEL, "model_revision": model_revision, "device": torch.cuda.get_device_name(0),
        "gpu_memory_gb": round(props.total_memory / 1024**3, 2), "cuda_version": torch.version.cuda,
        "torch_version": torch.__version__, "python_version": platform.python_version(),
        "document_count": len(documents), "evaluation_query_count": len(queries), "batch_size": BATCH_SIZE,
        "precision": "model FP16 where supported", "benchmark_repeats": REPEATS,
        "model_load_seconds": round(model_load_seconds, 3), "repeated_encode_seconds": round(encode_seconds, 3),
        "documents_per_second": round((len(documents) * REPEATS) / encode_seconds, 3),
        "peak_gpu_memory_mb": round(torch.cuda.max_memory_allocated() / 1024**2, 2),
        "configured_rate_usd_per_hour": rate or None,
        "estimated_compute_cost_usd": round(rate * duration / 3600, 4) if rate else None,
        "metrics": metrics, "source_corpus_sha256": hashlib.sha256((ROOT / "data/processed/gpu_corpus_manifest.json").read_bytes()).hexdigest(),
    }
    reports = ROOT / "reports/gpu"
    reports.mkdir(parents=True, exist_ok=True)
    (ROOT / "data/processed/gpu_related_streets.json").write_text(json.dumps({
        "schema_version": "1.0", "method": "BAAI/bge-m3 cosine similarity; GPU-generated and editorially bounded to published dossiers",
        "model": MODEL, "model_revision": model_revision, "generated_at": finished_at.isoformat(), "related": related,
    }, ensure_ascii=False, indent=2) + "\n")
    (reports / "retrieval_results.json").write_text(json.dumps({"metrics": metrics, "results": results}, ensure_ascii=False, indent=2) + "\n")
    (reports / "runpod_run_manifest.json").write_text(json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(run_manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
