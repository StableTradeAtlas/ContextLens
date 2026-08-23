import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.catalog import CATALOG, catalog_payload
from app.place_investigation import investigate_address, resolve_place


def run() -> None:
    payload = catalog_payload()
    assert payload["semantic_relations"]["available"] is True
    public_ids = {street["id"] for street in CATALOG}
    for street in payload["streets"]:
        assert len(street["related"]) == 3, street["id"]
        assert all(item["street_id"] in public_ids - {street["id"]} for item in street["related"])
    assert 3 <= len(CATALOG) <= 12
    seen = set()
    for street in CATALOG:
        assert street["id"] not in seen
        seen.add(street["id"])
        for field in ("address", "name_zh", "name_en", "intro_zh", "intro_en", "cover", "center"):
            assert street.get(field), (street["id"], field)
        resolved = resolve_place(street["address"], allow_live=False)
        assert len(resolved["candidates"]) == 1, street["id"]
        dossier = investigate_address(resolved["candidates"][0], address=street["address"], allow_live=False)
        dated = [item for item in dossier["timeline"] if item.get("start_year") or item.get("date")]
        assert len(dated) >= 2, (street["id"], "dated chronology")
        assert len(dossier["evidence"]) >= 3, (street["id"], "sources")
        assert dossier["experience"]["historical_maps"], (street["id"], "maps")
        assert all(item.get("source_uri") for item in dated), (street["id"], "source link")


if __name__ == "__main__":
    run()
    print("catalog publication tests passed")
