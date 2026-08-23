import React from "react";
import { Activity, FlaskConical, ListMusic, TimerReset } from "lucide-react";
import type { Job } from "../types";
import { BeatTable, DownloadsCard, SummaryCards, TimingCard, ValidationCard } from "../features/results";
import { BeatTimeline } from "./BeatTimeline";
import { RhythmLaboratory } from "./RhythmLaboratory";
import { Card, Tabs, TabsContent, TabsList, TabsTrigger } from "./ui";

export function ResultsPanel({ job }: { job: Job }) {
  const result = job.result;
  if (!result) return null;
  return <div className="space-y-4">
    <SummaryCards result={result} />
    <Tabs defaultValue="timeline">
      <TabsList className="w-full justify-start overflow-x-auto bg-white">
        <TabsTrigger value="timeline" className="flex items-center gap-1.5"><Activity className="h-3.5 w-3.5" />Timeline</TabsTrigger>
        <TabsTrigger value="beats" className="flex items-center gap-1.5"><ListMusic className="h-3.5 w-3.5" />Beats</TabsTrigger>
        <TabsTrigger value="details" className="flex items-center gap-1.5"><TimerReset className="h-3.5 w-3.5" />Details</TabsTrigger>
        {result.rhythm_interpretation && <TabsTrigger value="laboratory" className="flex items-center gap-1.5"><FlaskConical className="h-3.5 w-3.5" />Laboratory</TabsTrigger>}
      </TabsList>
      <TabsContent value="timeline"><Card title="Timeline" subtitle="Beat positions across the audio (D = downbeat)"><BeatTimeline result={result} /></Card></TabsContent>
      <TabsContent value="beats"><BeatTable result={result} /></TabsContent>
      <TabsContent value="details"><div className="grid grid-cols-1 gap-4 md:grid-cols-3"><TimingCard result={result} /><DownloadsCard job={job} result={result} /><ValidationCard result={result} /></div></TabsContent>
      {result.rhythm_interpretation && <TabsContent value="laboratory"><RhythmLaboratory interpretation={result.rhythm_interpretation} /></TabsContent>}
    </Tabs>
  </div>;
}
