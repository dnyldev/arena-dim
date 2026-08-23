import React, { useMemo } from "react";
import type { AnalysisResult } from "../types";

/**
 * Renders a horizontal timeline of beats / downbeats proportional to
 * the audio duration.  Downbeats are drawn as taller bars above the
 * beat number; ordinary beats are smaller ticks.
 *
 * The component is driven entirely by the result domain object — it
 * never touches raw backend responses.
 */
export function BeatTimeline({ result }: { result: AnalysisResult }) {
  const { beats, downbeats, beat_numbers, audio } = result;
  const duration = audio?.duration_sec ?? 0;

  const markers = useMemo(() => {
    const downSet = new Set(downbeats.map((d) => d.toFixed(4)));
    return beats.map((t, i) => ({
      t,
      number: beat_numbers[i] ?? i + 1,
      isDown: downSet.has(t.toFixed(4)),
    }));
  }, [beats, downbeats, beat_numbers]);

  if (!duration || beats.length === 0) {
    return (
      <div className="rounded-md border border-ink-200 bg-ink-50 px-4 py-6 text-center text-sm text-ink-500">
        No beats to display.
      </div>
    );
  }

  return (
    <div>
      <div className="relative h-20 w-full overflow-hidden rounded-md border border-ink-200 bg-white">
        {/* baseline */}
        <div className="absolute left-0 right-0 top-1/2 h-px bg-ink-200" />
        {markers.map((m, i) => {
          const left = `${Math.min(100, (m.t / duration) * 100)}%`;
          const height = m.isDown ? "h-12" : "h-5";
          const color = m.isDown ? "bg-brand-600" : "bg-ink-400";
          return (
            <div
              key={i}
              data-testid="beat-marker"
              className={`absolute top-1/2 w-px -translate-y-1/2 ${height} ${color}`}
              style={{ left }}
              title={`t=${m.t.toFixed(3)}s #${m.number}${
                m.isDown ? " (downbeat)" : ""
              }`}
            >
              {m.isDown && (
                <span className="absolute -top-4 left-1/2 -translate-x-1/2 text-[9px] font-semibold text-brand-700">
                  D
                </span>
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex justify-between font-mono text-[10px] text-ink-400">
        <span>0.0 s</span>
        <span>{duration.toFixed(2)} s</span>
      </div>
    </div>
  );
}
