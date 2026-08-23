import { useCallback, useRef, useState } from "react";
import { api, streamEvents } from "../api/client";
import type {
  AnalysisEvent,
  AnalysisRequest,
  Job,
} from "../types";

export type JobPhase =
  | "idle"
  | "uploading"
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

export function useJobState() {
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<AnalysisEvent[]>([]);
  const [phase, setPhase] = useState<JobPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<{ stage: string; pct: number | null }>({
    stage: "",
    pct: null,
  });
  const cancelRef = useRef<(() => void) | null>(null);

  const reset = useCallback(() => {
    cancelRef.current?.();
    setJob(null);
    setEvents([]);
    setPhase("idle");
    setError(null);
    setProgress({ stage: "", pct: null });
  }, []);

  const start = useCallback(
    async (file: File, config: AnalysisRequest) => {
      setError(null);
      setEvents([]);
      setPhase("uploading");
      setProgress({ stage: "upload", pct: null });
      try {
        const created = await api.analyze(file, config);
        setJob(created);
        setPhase(created.state === "queued" ? "queued" : "running");

        const stop = streamEvents(
          created.id,
          (ev) => {
            setEvents((prev) => [...prev, ev]);
            if (ev.stage !== "job") {
              setProgress({
                stage: ev.stage,
                pct: ev.progress,
              });
            }
            if (ev.status === "failed") {
              setError(ev.message);
            }
          },
          async () => {
            try {
              const final = await api.getJob(created.id);
              setJob(final);
              if (final.state === "completed") setPhase("completed");
              else if (final.state === "failed") {
                setPhase("failed");
                setError(final.error?.message ?? "Analysis failed");
              } else if (final.state === "cancelled") setPhase("cancelled");
            } catch {
              /* ignore */
            }
          }
        );
        cancelRef.current = stop;
      } catch (e) {
        setPhase("failed");
        setError(e instanceof Error ? e.message : "Request failed");
      }
    },
    []
  );

  const cancel = useCallback(async () => {
    if (!job) return;
    try {
      await api.cancelJob(job.id);
    } catch {
      /* may already be terminal */
    }
  }, [job]);

  return { job, events, phase, error, progress, start, reset, cancel };
}
