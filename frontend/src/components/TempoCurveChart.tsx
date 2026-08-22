import React, { useMemo, useState } from "react";
import type { TempoCurvePoint } from "../types";

/**
 * A lightweight SVG line chart of the tempo curve — local BPM over
 * time — with no external charting dependency.
 *
 * The curve is computed on the backend as a sliding window of median
 * BPM over consecutive beats (see `analysis/tempo.py`); this component
 * only renders it and lets the user hover for exact values.
 */
export function TempoCurveChart({
  curve,
  overallBpm,
  windowBeats,
  durationSec,
}: {
  curve: TempoCurvePoint[];
  overallBpm: number | null;
  windowBeats: number | null;
  durationSec: number;
}) {
  const [hover, setHover] = useState<number | null>(null);

  const width = 640;
  const height = 160;
  const padX = 8;
  const padY = 16;

  const { points, minBpm, maxBpm } = useMemo(() => {
    if (curve.length === 0) {
      return { points: [] as { x: number; y: number; p: TempoCurvePoint }[], minBpm: 0, maxBpm: 0 };
    }
    const bpms = curve.map((p) => p.bpm);
    let min = Math.min(...bpms);
    let max = Math.max(...bpms);
    if (min === max) {
      min -= 5;
      max += 5;
    } else {
      const margin = (max - min) * 0.1;
      min -= margin;
      max += margin;
    }
    const duration = durationSec || curve[curve.length - 1].time_sec || 1;
    const pts = curve.map((p) => ({
      x: padX + (p.time_sec / duration) * (width - 2 * padX),
      y:
        height -
        padY -
        ((p.bpm - min) / (max - min || 1)) * (height - 2 * padY),
      p,
    }));
    return { points: pts, minBpm: min, maxBpm: max };
  }, [curve, durationSec]);

  if (curve.length === 0) {
    return (
      <div className="rounded-md border border-ink-200 bg-ink-50 px-4 py-6 text-center text-sm text-ink-500">
        Not enough beats for a tempo curve.
      </div>
    );
  }

  const path = points
    .map((pt, i) => `${i === 0 ? "M" : "L"}${pt.x.toFixed(2)},${pt.y.toFixed(2)}`)
    .join(" ");

  const overallY =
    overallBpm != null
      ? height - padY - ((overallBpm - minBpm) / (maxBpm - minBpm || 1)) * (height - 2 * padY)
      : null;

  const hovered = hover != null ? points[hover] : null;

  return (
    <div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="w-full"
        role="img"
        aria-label="Tempo curve over time"
        onMouseLeave={() => setHover(null)}
      >
        {/* Reference line at overall median-IBI tempo */}
        {overallY != null && (
          <line
            x1={padX}
            x2={width - padX}
            y1={overallY}
            y2={overallY}
            stroke="#c7cdd6"
            strokeDasharray="4 3"
            strokeWidth={1}
          />
        )}
        <path d={path} fill="none" stroke="#4f46e5" strokeWidth={2} />
        {points.map((pt, i) => (
          <circle
            key={i}
            cx={pt.x}
            cy={pt.y}
            r={hover === i ? 4 : 2.5}
            fill="#4f46e5"
            onMouseEnter={() => setHover(i)}
          />
        ))}
      </svg>
      <div className="mt-1 flex items-center justify-between text-[10px] text-ink-400">
        <span>0.0 s</span>
        {windowBeats != null && (
          <span>window: {windowBeats} beats</span>
        )}
        <span>{durationSec.toFixed(2)} s</span>
      </div>
      <div className="mt-1 h-5 text-xs text-ink-600">
        {hovered ? (
          <span>
            t = {hovered.p.time_sec.toFixed(2)}s ·{" "}
            <span className="font-semibold">{hovered.p.bpm.toFixed(1)} BPM</span>
          </span>
        ) : (
          overallBpm != null && (
            <span className="text-ink-400">
              dashed line = overall tempo ({overallBpm.toFixed(1)} BPM)
            </span>
          )
        )}
      </div>
    </div>
  );
}
