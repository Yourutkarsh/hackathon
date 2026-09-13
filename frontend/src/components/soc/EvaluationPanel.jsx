import { useState } from "react";
import { BarChart3, Loader2, Target } from "lucide-react";
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
              <span>·</span>
              <span>detection: {data.detection_threshold}</span>
            </div>

            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Metric label="Precision" value={o.precision.toFixed(2)} />
              <Metric label="Recall" value={o.recall.toFixed(2)} />
              <Metric label="F1" value={o.f1.toFixed(2)} />
              <Metric label="FPR" value={o.false_positive_rate.toFixed(2)} />
            </div>
            <div className="grid grid-cols-4 gap-2 font-mono text-[11px]">
              <div className="rounded border border-emerald-500/30 bg-emerald-950/30 py-1.5 text-center text-emerald-400">TP {o.tp}</div>
              <div className="rounded border border-rose-500/30 bg-rose-950/30 py-1.5 text-center text-rose-400">FP {o.fp}</div>
              <div className="rounded border border-slate-700 bg-slate-800/50 py-1.5 text-center text-slate-300">TN {o.tn}</div>
              <div className="rounded border border-amber-500/30 bg-amber-950/30 py-1.5 text-center text-amber-400">FN {o.fn}</div>
            </div>

            <div>
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
                    {data.ablation.map((a) => (
                      <tr key={a.variant} className="border-t border-slate-800 text-slate-300">
                        <td className="p-2 text-cyan-400">{a.variant}</td>
                        <td className="p-2 text-right">{a.precision.toFixed(2)}</td>
                        <td className="p-2 text-right">{a.recall.toFixed(2)}</td>
                        <td className="p-2 text-right">{a.f1.toFixed(2)}</td>
                        <td className="p-2 text-right">{a.false_positive_rate.toFixed(2)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 font-body text-[11px] text-slate-500">
                Removing a component degrades detection — evidence that the score is a genuine
                multi-signal fusion, not a single hard-coded rule.
              </p>
            </div>

            <div>
              <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
                By Scenario
              </div>
              <div className="space-y-1">
                {Object.entries(data.by_scenario).map(([k, v]) => (
                  <div
                    key={k}
                    className="flex items-center justify-between rounded border border-slate-800 bg-slate-950/40 px-2.5 py-1.5 font-mono text-[11px]"
                  >
                    <span className="text-slate-300">{k}</span>
                    <span className="text-slate-500">
                      {v.detected_malicious}/{v.malicious} caught · {v.false_alarms} false alarms · {v.events} events
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
