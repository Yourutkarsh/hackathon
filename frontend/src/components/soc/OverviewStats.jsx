import { AlertTriangle, ShieldCheck, Gauge, TrendingUp } from "lucide-react";
import { SEVERITY, SEVERITY_ORDER, sevOf } from "@/lib/severity";

function StatCard({ children, testid }) {
  return (
    <div
      data-testid={testid}
      className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-4 transition-transform duration-200 hover:-translate-y-px hover:border-cyan-500/30"
    >
      {children}
    </div>
  );
}

export function OverviewStats({ revealed, topDrift, confidence }) {
  const counts = SEVERITY_ORDER.reduce((acc, k) => {
    acc[k] = revealed.filter((r) => r.severity === k).length;
    return acc;
  }, {});
  const activeAlerts = revealed.filter((r) =>
    ["ELEVATED", "HIGH", "CRITICAL"].includes(r.severity)
  ).length;

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <StatCard testid="stat-active-alerts">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-400">
            Active Alerts
          </span>
          <AlertTriangle className="h-4 w-4 text-amber-400" />
        </div>
        <div className="mt-2 font-heading text-3xl font-extrabold text-white">
          {activeAlerts}
        </div>
        <div className="mt-1 font-mono text-[11px] text-slate-500">
          {revealed.length} events processed
        </div>
      </StatCard>

      <StatCard testid="stat-severity-grid">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-400">
            Severity Spread
          </span>
          <ShieldCheck className="h-4 w-4 text-cyan-400" />
        </div>
        <div className="mt-3 grid grid-cols-4 gap-1.5">
          {SEVERITY_ORDER.map((k) => {
            const s = SEVERITY[k];
            return (
              <div key={k} className="text-center">
                <div
                  className="rounded-md border py-1.5 font-mono text-base font-bold"
                  style={{ borderColor: `${s.ring}44`, background: `${s.ring}12`, color: s.ring }}
                >
                  {counts[k]}
                </div>
                <div className="mt-1 font-mono text-[9px] uppercase tracking-wider text-slate-500">
                  {s.label}
                </div>
              </div>
            );
          })}
        </div>
      </StatCard>

      <StatCard testid="stat-confidence">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-400">
            Engine Confidence
          </span>
          <Gauge className="h-4 w-4 text-cyan-400" />
        </div>
        <div className="mt-2 flex items-end gap-2">
          <span className="font-heading text-3xl font-extrabold text-white">
            {confidence != null ? confidence : "\u2014"}
          </span>
          <span className="mb-1 font-mono text-xs text-slate-500">/ 100</span>
        </div>
        <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
          <div
            className="h-full rounded-full bg-cyan-400 transition-[width] duration-500"
            style={{ width: `${confidence || 0}%` }}
          />
        </div>
      </StatCard>

      <StatCard testid="stat-top-drift">
        <div className="flex items-center justify-between">
          <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-400">
            Top Drift Users
          </span>
          <TrendingUp className="h-4 w-4 text-orange-400" />
        </div>
        <div className="mt-2 space-y-1.5">
          {topDrift.length === 0 && (
            <div className="font-mono text-[11px] text-slate-600">
              Step the demo to populate
            </div>
          )}
          {topDrift.slice(0, 3).map((d) => (
            <div key={d.user_id} className="flex items-center justify-between">
              <span className="truncate font-body text-xs text-slate-300">{d.name}</span>
              <span className={`font-mono text-xs font-semibold ${sevOf(d.severity).text}`}>
                {d.risk_score.toFixed(1)}
              </span>
            </div>
          ))}
        </div>
      </StatCard>
    </div>
  );
}
