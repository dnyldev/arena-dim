import React, { useCallback, useRef, useState } from "react";
import { Badge } from "./Card";

export interface PickedFile {
  file: File;
  durationSec: number | null;
}

async function probeDuration(file: File): Promise<number | null> {
  // We don't import a heavy audio decode dependency; use an <audio>
  // element for a best-effort duration probe.
  return new Promise((resolve) => {
    try {
      const url = URL.createObjectURL(file);
      const a = document.createElement("audio");
      a.preload = "metadata";
      a.onloadedmetadata = () => {
        URL.revokeObjectURL(url);
        resolve(Number.isFinite(a.duration) ? a.duration : null);
      };
      a.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(null);
      };
      a.src = url;
    } catch {
      resolve(null);
    }
  });
}

export function FilePicker({
  onPick,
  disabled,
}: {
  onPick: (p: PickedFile) => void;
  disabled?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState<string>("");
  const [size, setSize] = useState<number>(0);
  const [duration, setDuration] = useState<number | null>(null);
  const [dragging, setDragging] = useState(false);

  const handle = useCallback(
    async (file: File) => {
      setName(file.name);
      setSize(file.size);
      const d = await probeDuration(file);
      setDuration(d);
      onPick({ file, durationSec: d });
    },
    [onPick]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        if (disabled) return;
        const f = e.dataTransfer.files?.[0];
        if (f) handle(f);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-8 text-center transition ${
        dragging
          ? "border-brand-500 bg-brand-50/50"
          : "border-ink-200 bg-white hover:border-brand-400 hover:bg-ink-50/60"
      } ${disabled ? "pointer-events-none opacity-60" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="audio/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handle(f);
        }}
      />
      <div className="text-3xl">🎵</div>
      <div className="mt-2 text-sm font-medium text-ink-700">
        {name ? name : "Drop an audio file here or click to browse"}
      </div>
      <div className="mt-1 flex items-center gap-2 text-xs text-ink-500">
        {size > 0 && <span>{(size / (1024 * 1024)).toFixed(2)} MB</span>}
        {duration != null && <span>· {duration.toFixed(2)} s</span>}
        {!name && <span>WAV, FLAC, MP3, M4A, OGG — ffmpeg for non-WAV</span>}
      </div>
      {name && (
        <div className="mt-3">
          <Badge tone="info">selected</Badge>
        </div>
      )}
    </div>
  );
}
