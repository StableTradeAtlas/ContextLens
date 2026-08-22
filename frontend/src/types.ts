export interface Candidate {
  candidate_id: string;
  canonical_name: string;
  display_name: string;
  historical_names: string[];
  modern_names: string[];
  name_periods: Array<{ name: string; from_year: number | null; to_year: number | null }>;
  confidence: number;
  match_reason: string;
  source_uri?: string;
  official_uri?: string;
}

export interface StoryChapter {
  chapter_id: string;
  year: number;
  title: string;
  title_en: string;
  caption: string;
  caption_en: string;
  duration_ms: number;
  center: [number, number];
  zoom: number;
  pitch: number;
  bearing: number;
  active_layers: string[];
  evidence_ids: string[];
  branch: string;
}

export interface HistoricalMapLayer {
  map_id: string;
  year: number;
  title: string;
  source_url: string;
  provider: string;
  license: string;
  attribution: string;
  overlay_status: "approximate_overlay" | "side_by_side" | string;
  image_url: string;
  iiif_manifest_url: string;
  annotation_url: string;
  bounds: [number, number, number, number] | number[];
  rms_error_m: number | null;
  error_threshold_m: number | null;
}

export interface LandmarkScene {
  model_id: string;
  title: string;
  title_en: string;
  longitude: number;
  latitude: number;
  start_year: number;
  end_year: number | null;
  height_m: number;
  width_m: number;
  depth_m: number;
  model_type: string;
  reconstruction_level: "A" | "B" | "C";
  reconstruction_note: string;
  source_uri: string;
  evidence_ids: string[];
}

export interface CuratedInteraction {
  interaction_id: string;
  interaction_type: string;
  title: string;
  title_en: string;
  prompt: string;
  prompt_en: string;
  evidence_ids: string[];
  payload: Record<string, unknown>;
  stamp_id: string;
}

export interface Experience {
  flagship: boolean;
  default_duration_seconds: number;
  duration_options: number[];
  chapters: StoryChapter[];
  historical_maps: HistoricalMapLayer[];
  landmark_scenes: LandmarkScene[];
  interactions: CuratedInteraction[];
  comparison: { year_a: number; year_b: number; anchors: number[] };
}

export interface InvestigationResult {
  candidate: Candidate;
  summary: string;
  finding: string;
  query: { focus_year: number; era_hint: number | null };
  timeline: Array<Record<string, any>>;
  claims: Array<Record<string, any>>;
  evidence: Array<Record<string, any>>;
  feature_collection: GeoJSON.FeatureCollection;
  map: Record<string, any>;
  quality: Record<string, any>;
  experience: Experience;
  media: Array<{
    asset_id: string; roads: string[]; kind: string; year: number | null; title: string; title_en?: string;
    description: string; description_en?: string; image_url: string; source_url: string; provider: string;
    creator: string; license: string; attribution: string; rights_status: string; evidence_role: string;
  }>;
  archive_network: {
    stats: Record<string, number>;
    datasets: Array<{ dataset_id: string; title: string; available_label: string; count: number; active: boolean }>;
    nodes: Array<Record<string, any>>;
    links: Array<{ source: string; target: string; relation: string; evidence_ids: string[] }>;
    people: Array<Record<string, any>>;
    organizations: Array<Record<string, any>>;
  };
}
