import { useState } from "react";
import { BarChart3, Loader2, Target, FlaskConical } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";

function Metric({ label, value }) {
  return (
    <div className="rounded-md border border-slate-800 bg-slate-950/40 p-3 text-center">
      <div className="font-heading text-2xl font-extrabold text-cyan-400">{value}</div>
      <div className="mt-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </div>
    </div>
  );
}

const pct = (v) => (typeof v === "number" ? v.toFixed(2) : "—");

function ConfusionRow({ c }) {
  return (
    <div className="grid grid-cols-4 gap-2 font-mono text-[11px]">
      <div className="rounded border border-emerald-500/30 bg-emerald-950/30 py-1.5 text-center text-emerald-400">TP {c?.tp ?? 0}</div>
      <div className="rounded border border-rose-500/30 bg-rose-950/30 py-1.5 text-center text-rose-400">FP {c?.fp ?? 0}</div>
      <div className="rounded border border-slate-700 bg-slate-800/50 py-1.5 text-center text-slate-300">TN {c?.tn ?? 0}</div>
      <div className="rounded border border-amber-500/30 bg-amber-950/30 py-1.5 text-center text-amber-400">FN {c?.fn ?? 0}</div>
    </div>
  );
}

export function EvaluationPanel() {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async (isOpen) => {
    setOpen(isOpen);
    if (isOpen && !data) {
      setLoading(true);
      try {
        setData(await api.evaluation());
      } finally {
        setLoading(false);
      }
    }
  };

  const o = data?.overall;
  const oL = data?.overall_legacy;
  const cal = data?.calibration;

  return (
    <Dialog open={open} onOpenChange={load}>
      <DialogTrigger asChild>
        <Button
          data-testid="evaluation-button"
          variant="outline"
          className="border-cyan-500/30 bg-cyan-950/20 text-cyan-300 hover:border-cyan-500/50 hover:text-cyan-200"
        >
          <BarChart3 className="mr-1.5 h-4 w-4" /> Evaluation &amp; Ablation
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] max-w-3xl overflow-y-auto border-slate-700 bg-slate-900 text-slate-100">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 font-heading">
            <Target className="h-4 w-4 text-cyan-400" /> Detection Evaluation
          </DialogTitle>
        </DialogHeader>

        {loading && (
          <div className="flex items-center gap-2 py-10 font-mono text-xs text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin text-cyan-400" /> scoring population against ground truth…
          </div>
        )}

        {data && (
          <div data-testid="evaluation-content" className="space-y-4">
            <div className="flex flex-wrap gap-3 font-mono text-[11px] text-slate-400">
              <span>{data.total_users} users</span>
              <span>·</span>
              <span>{data.total_trusted_events} trusted events</span>
            </div>

            {/* Adopted strict spec detection (HIGH/CRITICAL, 70+) */}
            <section>
              <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-400">
                Strict spec detection · {data.detection_threshold}
              </div>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <Metric label="Precision" value={pct(o?.precision)} />
                <Metric label="Recall" value={pct(o?.recall)} />
                <Metric label="F1" value={pct(o?.f1)} />
                <Metric label="FPR" value={pct(o?.false_positive_rate)} />
              </div>
              <div className="mt-2">
                <ConfusionRow c={o} />
              </div>
              <p className="mt-2 font-body text-[11px] text-slate-500">
                Adopted default: a detection requires severity HIGH/CRITICAL (score ≥ 70). The
                flagship Rahul E6 compound anomaly scores 67.98 (ELEVATED) — below this strict bar —
                so it is surfaced through the legacy alert band below and disclosed as a known
                boundary.
              </p>
            </section>

            {/* Legacy detection alias */}
            <section className="rounded-md border border-slate-800 bg-slate-950/40 p-3">
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Legacy alias · {data.detection_threshold_legacy}
              </div>
              <div className="grid grid-cols-4 gap-2 font-mono text-[11px] text-slate-300">
                <span>P {pct(oL?.precision)}</span>
                <span>R {pct(oL?.recall)}</span>
                <span>F1 {pct(oL?.f1)}</span>
                <span>FPR {pct(oL?.false_positive_rate)}</span>
              </div>
              <div className="mt-2">
                <ConfusionRow c={oL} />
              </div>
            </section>

            {/* Ablation ladder */}
            <section>
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
                Component Ablation
              </div>
              <div className="overflow-hidden rounded-md border border-slate-800">
                <table className="w-full text-left font-mono text-[11px]">
                  <thead className="bg-slate-950/60 text-slate-500">
                    <tr>
                      <th className="p-2">Variant</th>
                      <th className="p-2 text-right">Precision</th>
                      <th className="p-2 text-right">Recall</th>
                      <th className="p-2 text-right">F1</th>
                      <th className="p-2 text-right">FPR</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.ablation || []).map((a) => (
                      <tr key={a.variant} className="border-t border-slate-800 text-slate-300">
                        <td className="p-2 text-cyan-400">{a.variant}</td>
                        <td className="p-2 text-right">{pct(a.precision)}</td>
                        <td className="p-2 text-right">{pct(a.recall)}</td>
                        <td className="p-2 text-right">{pct(a.f1)}</td>
                        <td className="p-2 text-right">{pct(a.false_positive_rate)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 font-body text-[11px] text-slate-500">
                RULES_ONLY → RULES_PLUS_STATS → RULES_STATS_IFOREST builds the behavioral ladder;
                FULL is the fused model; TEMPORAL_OFF / CONTEXT_OFF ablate single components.
                Removing evidence degrades detection.
              </p>
              {(data.ablation_legacy || []).length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5 font-mono text-[10px] text-slate-500">
                  <span className="text-slate-600">legacy aliases:</span>
                  {data.ablation_legacy.map((a) => (
                    <span key={a.variant} className="rounded border border-slate-800 bg-slate-950/40 px-1.5 py-0.5">
                      {a.variant} → {a.aliased_variant}
                    </span>
                  ))}
                </div>
              )}
            </section>

            {/* Calibration sweep */}
            {cal && (
              <section className="rounded-md border border-cyan-500/20 bg-cyan-950/10 p-3">
                <div className="mb-2 flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.2em] text-cyan-400">
                  <FlaskConical className="h-3 w-3" /> Calibration Sweep (reporting-only)
                </div>
                <div className="grid grid-cols-2 gap-2 font-mono text-[11px] text-slate-300 sm:grid-cols-4">
                  <span>split {cal.split_ratio}</span>
                  <span>train {cal.split?.train}</span>
                  <span>cal {cal.split?.calibration}</span>
                  <span>lock {cal.split?.test}</span>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3 font-mono text-[11px] text-slate-300">
                  <span>
                    selected threshold:{" "}
                    <span className="text-cyan-300">{cal.selected_threshold}</span>
                  </span>
                  <span>target FPR ≤ {cal.target_fpr}</span>
                  {cal.fallback_used && (
                    <span className="rounded border border-amber-500/30 bg-amber-950/30 px-1.5 py-0.5 text-[10px] text-amber-400">
                      fallback used
                    </span>
                  )}
                </div>
                <div className="mt-2">
                  <div className="mb-1 font-mono text-[10px] uppercase tracking-wider text-slate-500">
                    Locked test slice
                  </div>
                  <ConfusionRow c={cal.locked_test_metrics} />
                  <div className="mt-1 grid grid-cols-4 gap-2 font-mono text-[11px] text-slate-300">
                    <span>P {pct(cal.locked_test_metrics?.precision)}</span>
                    <span>R {pct(cal.locked_test_metrics?.recall)}</span>
                    <span>F1 {pct(cal.locked_test_metrics?.f1)}</span>
                    <span>FPR {pct(cal.locked_test_metrics?.false_positive_rate)}</span>
                  </div>
                </div>
                <p className="mt-2 font-body text-[11px] text-slate-500">{cal.note}</p>
              </section>
            )}

            {/* By scenario */}
            <section>
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
                By Scenario
              </div>
              <div className="space-y-1">
                {Object.entries(data.by_scenario || {}).map(([k, v]) => (
                  <div
                    key={k}
                    className="flex items-center justify-between rounded border border-slate-800 bg-slate-950/40 px-2.5 py-1.5 font-mono text-[11px]"
                  >
                    <span className="text-slate-300">{k}</span>
                    <span className="text-slate-500">
                      {v.detected_malicious}/{v.malicious} spec · {v.detected_malicious_legacy}/{v.malicious} legacy ·{" "}
                      {v.false_alarms} FP · {v.events} events
                    </span>
                  </div>
                ))}
              </div>
              {data.scenario_aliases && (
                <p className="mt-2 font-mono text-[10px] text-slate-600">
                  alias: BENIGN → NORMAL
                </p>
              )}
            </section>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
