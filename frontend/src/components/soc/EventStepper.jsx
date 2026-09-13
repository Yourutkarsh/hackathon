import { MapPin, Ban, Clock } from "lucide-react";
import { sevOf } from "@/lib/severity";
import { cn } from "@/lib/utils";

export function EventStepper({ events, selectedEventId, revealedMap, onSelect }) {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-4">
      <div className="mb-3 flex items-center justify-between">
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-400">
          Chronological Event Stream
        </span>
        <span className="font-mono text-[10px] text-slate-600">
          click an event to investigate
        </span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2">
        {events.map((ev, i) => {
          const revealedSev = revealedMap[ev.event_id];
          const s = sevOf(revealedSev);
          const selected = ev.event_id === selectedEventId;
          const q = ev.quarantined;
          const local = (ev.timestamp_original || "").slice(11, 16) || "\u2014";
          const isAnomaly = revealedSev && ["ELEVATED", "HIGH", "CRITICAL"].includes(revealedSev);
          return (
            <button
              key={ev.event_id}
              data-testid={`event-stepper-item-${i + 1}`}
              onClick={() => onSelect(ev)}
              className={cn(
                "group relative flex min-w-[128px] shrink-0 flex-col gap-1 rounded-md border p-2.5 text-left transition-transform duration-200 hover:-translate-y-px",
                selected
                  ? "border-cyan-500/60 bg-cyan-500/10"
                  : "border-slate-700/70 bg-slate-950/40 hover:border-slate-600",
                isAnomaly && !selected && "border-amber-500/40"
              )}
              style={isAnomaly ? { boxShadow: `0 0 16px ${s.ring}33` } : undefined}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-slate-500">#{i + 1}</span>
                {q ? (
                  <Ban className="h-3 w-3 text-slate-600" />
                ) : (
                  <span className={cn("h-2 w-2 rounded-full", revealedSev ? s.dot : "bg-slate-700")} />
                )}
              </div>
              <div className="truncate font-body text-xs font-medium text-slate-200">
                {ev.event_type || "event"}
              </div>
              <div className="flex items-center gap-1 text-slate-500">
                <MapPin className="h-3 w-3" />
                <span className="truncate font-mono text-[10px]">
                  {ev.location?.city || "unknown"}
                </span>
              </div>
              <div className="flex items-center gap-1 text-slate-500">
                <Clock className="h-3 w-3" />
                <span className="font-mono text-[10px]">{local}</span>
              </div>
              {q && (
                <span className="mt-0.5 rounded bg-slate-800 px-1 py-0.5 font-mono text-[8px] uppercase tracking-wider text-slate-500">
                  quarantined
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
