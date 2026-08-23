import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import type { EngineSpec, Health, ModelInfo } from "../types";

export function useHealthState() {
  const [health, setHealth] = useState<Health | null>(null);
  const [spec, setSpec] = useState<EngineSpec | null>(null);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [h, s, m] = await Promise.all([
        api.health(),
        api.spec(),
        api.models(),
      ]);
      setHealth(h);
      setSpec(s);
      setModels(m);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to reach backend");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial network synchronization; state updates occur after awaited I/O.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refresh();
  }, [refresh]);

  return { health, spec, models, error, loading, refresh };
}
