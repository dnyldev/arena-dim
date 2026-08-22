import { useCallback, useState } from "react";
import type { AnalysisRequest } from "../types";

const DEFAULTS: AnalysisRequest = {
  checkpoint: "final0",
  dbn: false,
  float16: false,
  want_beats_file: true,
  want_json: true,
  want_activations: false,
};

export function useConfigurationState(initial?: Partial<AnalysisRequest>) {
  const [config, setConfig] = useState<AnalysisRequest>({
    ...DEFAULTS,
    ...initial,
  });

  const update = useCallback(<K extends keyof AnalysisRequest>(
    key: K,
    value: AnalysisRequest[K]
  ) => {
    setConfig((c) => ({ ...c, [key]: value }));
  }, []);

  return { config, update, setConfig };
}
