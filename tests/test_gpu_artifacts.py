import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run() -> None:
    manifest = json.loads((ROOT / "reports/gpu/runpod_run_manifest.json").read_text())
    results = json.loads((ROOT / "reports/gpu/retrieval_results.json").read_text())
    relations = json.loads((ROOT / "data/processed/gpu_related_streets.json").read_text())
    corpus = json.loads((ROOT / "data/processed/gpu_corpus_manifest.json").read_text())

    assert manifest["device"].startswith("NVIDIA RTX PRO 6000")
    assert manifest["model"] == "BAAI/bge-m3"
    assert manifest["document_count"] == 9
    assert manifest["evaluation_query_count"] == 30
    assert 0 <= manifest["metrics"]["recall_at_1"] <= 1
    assert 0 <= manifest["metrics"]["recall_at_3"] <= 1
    assert len(results["results"]) == 30
    assert corpus["document_count"] == 9
    assert corpus["query_count"] == 30
    assert len(relations["related"]) == 9
    assert all(len(items) == 3 for items in relations["related"].values())


if __name__ == "__main__":
    run()
    print("GPU artifact tests passed")
