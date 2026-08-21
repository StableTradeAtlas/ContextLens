from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EvidenceRecord:
    record_id: str
    title: str
    snippet: str
    source: str
    source_uri: str
    dataset: str
    date: str = ""
    persons: list[str] = field(default_factory=list)
    places: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    is_live_api: bool = False
    evidence_type: str = "source_record"
    provenance_note: str = ""
    time_span: str = ""
    geo: dict[str, Any] = field(default_factory=dict)
    public_tags: list[str] = field(default_factory=list)
    verification_notes: list[str] = field(default_factory=list)
    lineage: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RetrievalResult:
    record: EvidenceRecord
    score: float
    matched_terms: list[str]

    def to_dict(self) -> dict[str, Any]:
        data = self.record.to_dict()
        data["score"] = self.score
        data["matched_terms"] = self.matched_terms
        return data


@dataclass
class PlaceCandidate:
    """A time-aware place identity returned by the old-address resolver."""

    candidate_id: str
    canonical_name: str
    display_name: str
    historical_names: list[str] = field(default_factory=list)
    modern_names: list[str] = field(default_factory=list)
    valid_from: int | None = None
    valid_to: int | None = None
    official_uri: str = ""
    source_uri: str = ""
    confidence: float = 0.0
    match_reason: str = ""
    resolution_status: str = "candidate"
    house_number: str = ""
    name_periods: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HistoricalFeature:
    """A map feature whose geometry, time range, and provenance stay explicit."""

    feature_id: str
    feature_type: str
    title: str
    description: str
    source_uri: str
    source_title: str
    start_year: int | None = None
    end_year: int | None = None
    longitude: float | None = None
    latitude: float | None = None
    spatial_precision: str = "unknown"
    address: str = ""
    people: list[str] = field(default_factory=list)
    organizations: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    live_api: bool = False

    def to_geojson_feature(self) -> dict[str, Any]:
        geometry = None
        if self.longitude is not None and self.latitude is not None:
            geometry = {"type": "Point", "coordinates": [self.longitude, self.latitude]}
        properties = asdict(self)
        properties.pop("longitude", None)
        properties.pop("latitude", None)
        return {
            "type": "Feature",
            "id": self.feature_id,
            "geometry": geometry,
            "properties": properties,
        }


@dataclass
class HistoricalClaim:
    """A relation-level claim that cannot be marked direct without evidence gates."""

    claim_id: str
    subject: str
    predicate: str
    object: str
    text: str
    evidence_ids: list[str] = field(default_factory=list)
    support_level: str = "context"
    audit_status: str = "review"
    confidence: float = 0.0
    start_year: int | None = None
    end_year: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class HistoricalMapLayer:
    """A historical scan with explicit reuse and georeferencing boundaries."""

    map_id: str
    year: int
    title: str
    source_url: str
    provider: str
    license: str
    attribution: str
    overlay_status: str = "side_by_side"
    image_url: str = ""
    iiif_manifest_url: str = ""
    annotation_url: str = ""
    bounds: list[float] = field(default_factory=list)
    rms_error_m: float | None = None
    error_threshold_m: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StoryChapter:
    """One evidence-bound camera and time beat in the curated director."""

    chapter_id: str
    year: int
    title: str
    title_en: str
    caption: str
    caption_en: str
    duration_ms: int
    center: list[float]
    zoom: float
    pitch: float = 0.0
    bearing: float = 0.0
    active_layers: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    branch: str = "main"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LandmarkScene:
    """A time-aware, source-backed landmark massing in geographic space."""

    model_id: str
    title: str
    title_en: str
    longitude: float
    latitude: float
    start_year: int
    end_year: int | None
    height_m: float
    width_m: float
    depth_m: float
    model_type: str
    reconstruction_level: str
    reconstruction_note: str
    source_uri: str
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CuratedInteraction:
    """A non-punitive interaction whose answer is fixed by verified evidence."""

    interaction_id: str
    interaction_type: str
    title: str
    title_en: str
    prompt: str
    prompt_en: str
    evidence_ids: list[str]
    payload: dict[str, Any] = field(default_factory=dict)
    stamp_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
