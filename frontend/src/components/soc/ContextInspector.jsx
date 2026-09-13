import { SlidersHorizontal, CheckCircle2, XCircle } from "lucide-react";

export function ContextInspector({ investigation }) {
  if (!investigation) return null;
  const contexts = investigation.evidence?.contexts_considered || [];

  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-5">
      <div className="mb-4 flex items-center gap-2">
        <SlidersHorizontal className="h-4 w-4 text-cyan-400" />
        <h3 className="font-heading text-base font-semibold text-white">
          Context Discount Inspector
        </h3>
      </div>

      {contexts.length === 0 && (
        <div className="rounded border border-slate-800 bg-slate-950/40 px-3 py-2 font-mono text-[11px] text-slate-500">
          No context records for this subject — all evidence counts at full weight.
        </div>
      )}

      <div className="space-y-2">
        {contexts.map((c) => {
          const applicable = c.time_valid_at_event;
          return (
            <div
              key={c.context_id}
              className={`rounded-md border p-3 ${
                applicable
                  ? "border-emerald-500/30 bg-emerald-950/20"
                  : "border-slate-700/70 bg-slate-950/40"
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-[11px] text-slate-300">{c.context_id}</span>
                {applicable ? (
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-emerald-400">
                    <CheckCircle2 className="h-3 w-3" /> applicable — discount active
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                    <XCircle className="h-3 w-3" /> expired — no discount
                  </span>
                )}
              </div>
              <div className="mt-1.5 font-body text-xs text-slate-400">{c.reason}</div>
              <div className="mt-1.5 flex flex-wrap gap-1">
                {(c.affected_signal_families || []).map((f) => (
                  <span
                    key={f}
                    className="rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 font-mono text-[9px] text-slate-400"
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <p className="mt-3 font-body text-[11px] leading-relaxed text-slate-500">
        Discounts only apply to <span className="text-slate-300">targeted, time-valid</span> context
        windows. Independent evidence outside a context window is never reduced.
      </p>
    </div>
  );
}
