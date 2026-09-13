import { ScrollText } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

const ACTION_STYLE = {
  ANALYST_INVESTIGATION: "text-cyan-400 border-cyan-500/30 bg-cyan-950/40",
  ASSISTANT_QUERY: "text-violet-300 border-violet-500/30 bg-violet-950/40",
  FLAGGED_BY_DEMO: "text-amber-400 border-amber-500/30 bg-amber-950/40",
  ANALYST_NOTE: "text-slate-300 border-slate-600/40 bg-slate-800/50",
  ANALYST_ESCALATE: "text-orange-400 border-orange-500/30 bg-orange-950/40",
  ANALYST_DISMISS: "text-rose-400 border-rose-500/30 bg-rose-950/40",
};

export function AuditTrail({ records }) {
  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-5">
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <ScrollText className="h-4 w-4 text-cyan-400" />
          <h3 className="font-heading text-base font-semibold text-white">Audit Trail</h3>
        </div>
        <span className="rounded border border-slate-700 bg-slate-800/60 px-2 py-0.5 font-mono text-[10px] text-slate-500">
          {records.length} record(s) · immutable
        </span>
      </div>

      <ScrollArea className="h-[240px] pr-3">
        <div data-testid="audit-trail-list" className="space-y-1.5">
          {records.length === 0 && (
            <div className="font-mono text-[11px] text-slate-600">no audit records yet</div>
          )}
          {[...records].reverse().map((r) => (
            <div
              key={r.audit_id}
              data-testid="audit-record"
              className="flex items-start gap-2 rounded-md border border-slate-800 bg-slate-950/40 px-2.5 py-2"
            >
              <span
                className={`shrink-0 rounded border px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider ${
                  ACTION_STYLE[r.action] || "text-slate-400 border-slate-700 bg-slate-800/50"
                }`}
              >
                {r.action.replace("ANALYST_", "").replace("_", " ")}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 font-mono text-[11px] text-slate-300">
                  <span className="truncate">{r.event_id || r.user_id}</span>
                  <span className="text-slate-600">·</span>
                  <span className="text-slate-500">
                    {r.severity} {typeof r.risk_score === "number" ? r.risk_score.toFixed(1) : ""}
                  </span>
                  {r.dismissed && (
                    <span className="rounded bg-rose-950/50 px-1 font-mono text-[8px] uppercase text-rose-400">
                      dismissed (workflow)
                    </span>
                  )}
                </div>
                {r.note && (
                  <div className="mt-0.5 truncate font-body text-[11px] text-slate-500">
                    {r.note}
                  </div>
                )}
                <div className="mt-0.5 font-mono text-[9px] text-slate-600">
                  {(r.created_at || "").replace("T", " ").slice(0, 19)}
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
