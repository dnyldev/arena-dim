import type {
  AnalysisEvent,
  AnalysisRequest,
  EngineSpec,
  Health,
  Job,
  ModelInfo,
} from "../types";

const BASE = "/api";

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      /* ignore */
    }
    const message =
      (detail as { error?: { message?: string } } | null)?.error?.message ??
      (typeof detail === "string" ? detail : `HTTP ${res.status}`);
    const err = new Error(message) as Error & {
      status: number;
      detail: unknown;
    };
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => fetch(`${BASE}/health`).then((r) => jsonOrThrow<Health>(r)),
  spec: () => fetch(`${BASE}/spec`).then((r) => jsonOrThrow<EngineSpec>(r)),
  models: () =>
    fetch(`${BASE}/models`).then((r) => jsonOrThrow<ModelInfo[]>(r)),
  preloadModel: (checkpoint: string) =>
    fetch(`${BASE}/models/preload/${checkpoint}`, { method: "POST" }).then(
      (r) => jsonOrThrow<{ checkpoint: string; status: string }>(r)
    ),

  analyze: (file: File, config: AnalysisRequest): Promise<Job> => {
    const fd = new FormData();
    fd.append("audio", file);
    fd.append("config", JSON.stringify(config));
    return fetch(`${BASE}/analysis`, { method: "POST", body: fd }).then((r) =>
      jsonOrThrow<Job>(r)
    );
  },

  getJob: (id: string) =>
    fetch(`${BASE}/jobs/${id}`).then((r) => jsonOrThrow<Job>(r)),

  listJobs: (limit = 20) =>
    fetch(`${BASE}/jobs?limit=${limit}`).then((r) => jsonOrThrow<Job[]>(r)),

  cancelJob: (id: string) =>
    fetch(`${BASE}/jobs/${id}/cancel`, { method: "POST" }).then((r) =>
      jsonOrThrow<Job>(r)
    ),

  events: (id: string) =>
    fetch(`${BASE}/jobs/${id}/events`).then((r) =>
      jsonOrThrow<AnalysisEvent[]>(r)
    ),

  artifactUrl: (jobId: string, name: string) =>
    `${BASE}/jobs/${jobId}/artifacts/${name}`,
};

export function streamEvents(
  jobId: string,
  onEvent: (e: AnalysisEvent) => void,
  onDone: () => void
): () => void {
  const es = new EventSource(`${BASE}/jobs/${jobId}/events/stream`);
  es.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data) as AnalysisEvent;
      onEvent(data);
      if (data.stage === "job" && (data.status === "completed" || data.status === "failed")) {
        onDone();
        es.close();
      }
    } catch {
      /* ignore malformed */
    }
  };
  es.onerror = () => {
    onDone();
    es.close();
  };
  return () => es.close();
}
