import { Cpu, CheckCircle2, MinusCircle, GitBranch } from "lucide-react";
import { cn } from "@/lib/utils";

const FALLBACK_LABELS = {
  insufficient_user_history: "Population fallback — user history below minimum",
  insufficient_training_population: "No valid training population (score withheld)",
};

function fmt(v, d = 4) {
  return typeof v === "number" ? v.toFixed(d) : "—";
}

export function ModelMetadata({ investigation }) {
  if (!investigation) return null;
  const model = investigation.iforest_model || {};
  const info = investigation.iforest || {};
  const channels = investigation.behavioral_channels || {};
  const available = !!info.available;

  return (
    <div
      data-testid="model-metadata"
      className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-5"
    >
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-cyan-400" />
          <h3 className="font-heading text-base font-semibold text-white">
            Isolation Forest Channel
          </h3>
        </div>
        <span className="font-mono text-[10px] text-slate-500">
          {info.model || model.model_version || "iforest-v1"}
        </span>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        {available ? (
          <span className="inline-flex items-center gap-1 rounded border border-cyan-500/30 bg-cyan-950/40 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-cyan-400">
            <CheckCircle2 className="h-3 w-3" /> available
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 rounded border border-slate-700 bg-slate-800/60 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-500">
            <MinusCircle className="h-3 w-3" /> unavailable
          </span>
        )}
        {info.source && (
          <span
            className={cn(
              "inline-flex items-center gap-1 rounded border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider",
              info.source === "user"
                ? "border-emerald-500/30 bg-emerald-950/40 text-emerald-400"
                : "border-amber-500/30 bg-amber-950/40 text-amber-400"
            )}
          >
            <GitBranch className="h-3 w-3" /> {info.source} model
          </span>
        )}
      </div>

      {info.fallback_reason && (
        <div className="mb-3 rounded border border-amber-500/20 bg-amber-950/20 px-2.5 py-1.5 font-mono text-[10px] text-amber-300">
          {FALLBACK_LABELS[info.fallback_reason] || info.fallback_reason}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 font-mono text-[11px] sm:grid-cols-3">
        <Cell label="raw score" value={fmt(info.raw_score)} />
        <Cell label="scaled (0-100)" value={fmt(info.scaled_score, 2)} />
        <Cell label="q95" value={fmt(info.q95)} />
        <Cell label="q99" value={fmt(info.q99)} />
        <Cell label="train events" value={info.training_count ?? "—"} />
        <Cell label="min history" value={info.min_history ?? "—"} />
      </div>

      <div className="mt-4 border-t border-slate-800 pt-3">
        <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
          Behavioral Sub-channels
        </div>
        <div className="grid grid-cols-3 gap-2">
          <Channel label="Rules" value={channels.rules} />
          <Channel label="Statistics" value={channels.statistical} />
          <Channel label="IForest" value={channels.iforest} />
        </div>
        <p className="mt-2 font-body text-[11px] leading-relaxed text-slate-500">
          The behavioral component is the max of its available channels. The Isolation Forest is
          trained on strictly-prior history; a score is never fabricated when no valid training
          population exists.
        </p>
      </div>
    </div>
  );
}

function Cell({ label, value }) {
  return (
    <div className="rounded border border-slate-800 bg-slate-950/40 px-2 py-1.5">
      <div className="font-mono text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
      <div className="text-slate-200">{value ?? "—"}</div>
    </div>
  );
}

function Channel({ label, value }) {
  const present = typeof value === "number";
  return (
    <div className="rounded border border-slate-800 bg-slate-950/40 p-2 text-center">
      <div
        className={cn(
          "font-heading text-lg font-bold",
          present ? "text-cyan-400" : "text-slate-600"
        )}
      >
        {present ? value.toFixed(1) : "—"}
      </div>
      <div className="font-mono text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
    </div>
  );
}
