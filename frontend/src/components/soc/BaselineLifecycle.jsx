import { Layers3, CheckCircle2, CircleDot } from "lucide-react";
import { cn } from "@/lib/utils";
import { baselineOf as baselineMeta } from "@/lib/severity";

export function BaselineLifecycle({ lifecycle, version }) {
  const lc = lifecycle || {};
  const state = lc.state || "COLD";
  const meta = baselineMeta(state);
  const thresholds = lc.thresholds || {};
  const reasons = lc.readiness_reasons || [];
  const versionValue = version ?? lc.baseline_version;

  return (
    <div
      data-testid="baseline-lifecycle"
      className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers3 className="h-4 w-4 text-cyan-400" />
          <h3 className="font-heading text-base font-semibold text-white">
            Baseline Lifecycle
          </h3>
        </div>
        <span
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.15em]",
            meta.badge
          )}
        >
          <span className={cn("h-1.5 w-1.5 rounded-full", meta.dot)} />
          {meta.label}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2">
        <Stat label="Trusted events" value={lc.event_count ?? "—"} />
        <Stat label="Distinct days" value={lc.distinct_days ?? "—"} />
        <Stat label="Baseline version" value={versionValue ?? "—"} />
      </div>

      <p className="mt-3 font-body text-[11px] leading-relaxed text-slate-500">
        {meta.hint}
      </p>

      {reasons.length > 0 && (
        <ul className="mt-2 space-y-1">
          {reasons.map((r) => (
            <li
              key={r}
              className="flex items-center gap-1.5 font-mono text-[10px] text-amber-400/90"
            >
              <CircleDot className="h-2.5 w-2.5" /> {r}
            </li>
          ))}
        </ul>
      )}

      {reasons.length === 0 && (
        <div className="mt-2 flex items-center gap-1.5 font-mono text-[10px] text-emerald-400">
          <CheckCircle2 className="h-3 w-3" /> READY — full fusion baseline
        </div>
      )}

      <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 border-t border-slate-800 pt-2 font-mono text-[10px] text-slate-600">
        <span>COLD &lt; {thresholds.cold_below_events ?? 20} events</span>
        <span>READY ≥ {thresholds.ready_min_events ?? 50} events</span>
        <span>READY ≥ {thresholds.ready_min_days ?? 7} distinct days</span>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950/40 p-2.5 text-center">
      <div className="font-heading text-xl font-extrabold text-cyan-400">{value}</div>
      <div className="mt-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
        {label}
      </div>
    </div>
  );
}
