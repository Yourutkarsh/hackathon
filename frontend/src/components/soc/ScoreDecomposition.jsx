import { Layers, CheckCircle2, MinusCircle } from "lucide-react";
import { COMPONENTS, fmtNum } from "@/lib/severity";
import { cn } from "@/lib/utils";

export function ScoreDecomposition({ investigation }) {
  if (!investigation) return null;
  const values = investigation.components || {};
  const avail = investigation.component_availability || {};
  const families = investigation.active_signal_families || [];

  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-5">
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="h-4 w-4 text-cyan-400" />
          <h3 className="font-heading text-base font-semibold text-white">
            Component Decomposition
          </h3>
        </div>
        <span className="font-mono text-[10px] text-slate-500">weighted → engine score</span>
      </div>

      <div className="space-y-3">
        {COMPONENTS.map((c) => {
          const v = values[c.key];
          const isAvail = !!avail[c.key];
          const pct = Math.max(0, Math.min(100, Number(v) || 0));
          const isDiscount = c.key === "context_adjustment";
          return (
            <div key={c.key} data-testid={`score-component-row-${c.key}`} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-body text-xs text-slate-200">
                    <span className="mr-1 font-mono text-slate-500">{c.sign}</span>
                    {c.label}
                  </span>
                  {isAvail ? (
                    <span className="inline-flex items-center gap-1 rounded border border-cyan-500/30 bg-cyan-950/40 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-400">
                      <CheckCircle2 className="h-2.5 w-2.5" /> available
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
                      <MinusCircle className="h-2.5 w-2.5" /> unavailable
                    </span>
                  )}
                </div>
                <span
                  className={cn(
                    "font-mono text-sm font-semibold",
                    !isAvail ? "text-slate-600" : isDiscount ? "text-emerald-400" : "text-slate-100"
                  )}
                >
                  {fmtNum(v)}
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800/80">
                <div
                  className={cn(
                    "h-full rounded-full transition-[width] duration-700 ease-out",
                    !isAvail ? "bg-slate-700" : isDiscount ? "bg-emerald-500" : "bg-gradient-to-r from-cyan-500 to-amber-400"
                  )}
                  style={{ width: `${isAvail ? pct : 0}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-4 border-t border-slate-800 pt-3">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
          Active Signal Families
        </div>
        <div className="flex flex-wrap gap-1.5">
          {families.length === 0 && (
            <span className="font-mono text-[11px] text-slate-600">none active</span>
          )}
          {families.map((f) => (
            <span
              key={f}
              className="rounded border border-amber-500/30 bg-amber-950/40 px-2 py-0.5 font-mono text-[10px] text-amber-300"
            >
              {f}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
