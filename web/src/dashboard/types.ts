export type ModelKey = 'general' | 'ghost-gear';
export type Profile = 'general' | 'ghostvision' | 'aquascan' | 'mine' | 'sctd' | 'subpipe';

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
  packs: { json: string; html: string };
  profile: Profile;
  tta: boolean;
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
