export type ModelKey = 'general' | 'ghost-gear';
export type Profile = 'general' | 'ghostvision' | 'aquascan' | 'mine' | 'sctd' | 'subpipe';
export type ClaimLevel = 'calibrated' | 'indicative' | 'withdrawn';
export type Ellipse95 = [number, number, number];

export interface Contact {
  id: string;
  box: [number, number, number, number];
  raw_score: number;
  probability: number;
  flagged: boolean;
  evidence: Record<string, unknown>;
}

export interface SurveyImage {
  index: number;
  name: string;
  width: number;
  height: number;
  url: string;
  detections: Contact[];
}

export interface Position {
  lon: number;
  lat: number;
  map_x: number;
  map_y: number;
  ellipse95: Ellipse95 | null;
  cov_en_m2: number[][];
  method: string;
  assumed_georef_sigma_m: number;
}

export interface CompletenessCell {
  image_index: number;
  row: number;
  col: number;
  box: [number, number, number, number];
  n_trials: number;
  n_detected: number;
  pd: number;
  pd_lower: number;
  status: 'ok' | 'insufficient_trials';
}

export interface MeasuredCompleteness {
  available: true;
  claim_level: ClaimLevel;
  method: string;
  library_size: number;
  profile: string;
  grid: [number, number];
  trials: number;
  detected: number;
  pd: number;
  pd_lower90: number;
  cells_ok: number;
  caveat: string;
  cells: CompletenessCell[];
}

export type Completeness = MeasuredCompleteness | { available: false; reason: string };

export interface Packs {
  json: string;
  html: string;
  geojson: string;
  kml: string;
  csv: string;
  plan: string;
  completeness?: string;
  [key: `completeness_tif_${number}`]: string | undefined;
}

export interface VerificationPlan {
  entries: {
    rank: number;
    contact_id: string;
    lon: number;
    lat: number;
    p_real: number;
    ellipse95: Ellipse95 | null;
    claim_level: ClaimLevel;
    cumulative_expected_real: number;
  }[];
  expected_real_total: number;
  excluded_withdrawn: number;
  excluded_no_position: number;
  note: string;
}

export interface Analysis {
  survey_id: string;
  model: { id: string; label: string; model_class: string };
  claim: { level: string; statement: string; reasons: string[] };
  operating: {
    threshold: number | null;
    budget: number;
    flagged: number;
    recall: number | null;
    recall_ci: [number | null, number | null];
    recall_source: string;
  };
  images: SurveyImage[];
  timing_ms: number;
  packs: Packs;
  profile: Profile;
  tta: boolean;
  georeferenced: boolean[];
  positions: Record<string, Position>;
  completeness: Completeness | null;
}

export interface Sample {
  id: string;
  name: string;
  dataset: string;
  group: string;
  width: number;
  height: number;
  url: string;
}

export interface Health {
  ok: boolean;
  device: string;
  models: { key: ModelKey; label: string; model_class: string; model_id: string }[];
}

export interface Session {
  result: Analysis;
  urls: string[];
  model: ModelKey;
  files: File[];
  sampleIds: string[];
  completeness: boolean;
}

export const profiles: { value: Profile; label: string }[] = [
  { value: 'general', label: 'General' },
  { value: 'ghostvision', label: 'Crab pots · GhostVision' },
  { value: 'aquascan', label: 'People · AquaScan' },
  { value: 'mine', label: 'Mine-like' },
  { value: 'sctd', label: 'Wrecks & aircraft · SCTD' },
  { value: 'subpipe', label: 'Pipelines · SubPipe' },
];

export const percent = (n: number | null | undefined) =>
  n == null ? '—' : `${(n * 100).toFixed(1)}%`;

export function cellDescription(cell: CompletenessCell): string {
  return `Pd ≥ ${percent(cell.pd_lower)} (90% lower bound), ${cell.n_detected} of ${cell.n_trials} injected targets found${cell.status === 'insufficient_trials' ? ' · too few trials' : ''}`;
}

/** Shared colour scale for the canvas, legend and mini-grids. */
export function completenessColor(value: number): string {
  const t = Math.max(0, Math.min(1, value));
  return `color-mix(in srgb, var(--ns-completeness-low) ${(1 - t) * 100}%, var(--ns-completeness-high))`;
}

export function exportLinks(packs: Packs): { id: string; label: string; url: string }[] {
  const links = [
    { id: 'geojson', label: 'GeoJSON', url: packs.geojson },
    { id: 'kml', label: 'KML', url: packs.kml },
    { id: 'csv', label: 'CSV', url: packs.csv },
    { id: 'plan', label: 'Verification plan (JSON)', url: packs.plan },
    ...(packs.completeness ? [{ id: 'completeness', label: 'Completeness (JSON)', url: packs.completeness }] : []),
  ];
  Object.entries(packs)
    .filter(([key, url]) => /^completeness_tif_\d+$/.test(key) && !!url)
    .sort(([a], [b]) => Number(a.slice(a.lastIndexOf('_') + 1)) - Number(b.slice(b.lastIndexOf('_') + 1)))
    .forEach(([id, url]) => {
      if (url) links.push({ id, label: `Completeness GeoTIFF · image ${Number(id.slice(id.lastIndexOf('_') + 1)) + 1}`, url });
    });
  return links.filter(link => !!link.url);
}

export async function api<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error('Cannot reach the local API. Start it with: uv run python -m netsight.app.server --port 8000');
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: unknown } | null;
    throw new Error(typeof body?.detail === 'string'
      ? body.detail
      : `API returned ${response.status}. Check the API terminal. Start: uv run python -m netsight.app.server --port 8000`);
  }
  return response.json() as Promise<T>;
}

/** Same count operating point: kth-largest raw score, with boundary ties included.
 * Null means an infinite threshold, i.e. floor(budget × images) is zero.
 */
export function operatingPreview(result: Analysis, budget: number) {
  const scores = result.images.flatMap(image => image.detections.map(d => d.raw_score))
    .sort((a, b) => b - a);
  const count = Math.min(scores.length, Math.floor(budget * result.images.length));
  const threshold = count === 0 ? null : scores[count - 1];
  const flags = new Set(
    result.images.flatMap(image => image.detections)
      .filter(d => threshold !== null && d.raw_score >= threshold)
      .map(d => d.id),
  );
  return { threshold, flags, target: count };
}
