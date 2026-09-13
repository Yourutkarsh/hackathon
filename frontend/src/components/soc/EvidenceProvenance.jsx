import { Fingerprint, Terminal, Boxes, ShieldQuestion } from "lucide-react";

const RULE_LABELS = {
  RULE_A_AFTER_HOURS: "Rule A · After-hours deviation",
  RULE_B_NOVEL_SENSITIVE_RESOURCE: "Rule B · Novel sensitive resource",
  RULE_C_VOLUME_SPIKE: "Rule C · Volume spike",
  RULE_D_RAPID_BURST: "Rule D · Rapid burst",
  RULE_E_MULTI_FAMILY: "Rule E · Multi-family",
};

export function EvidenceProvenance({ investigation }) {
  if (!investigation) return null;
  const ev = investigation.evidence || {};
  const target = ev.target_event || {};
  const ruleScores = ev.rule_scores || {};
  const clusters = investigation.clusters || [];

  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-5">
      <div className="mb-4 flex items-center gap-2">
        <Fingerprint className="h-4 w-4 text-cyan-400" />
        <h3 className="font-heading text-base font-semibold text-white">
          Evidence &amp; Provenance
        </h3>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Fired detectors */}
        <div>
          <div className="mb-2 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
            <Terminal className="h-3 w-3" /> Fired Detectors
          </div>
          <div className="space-y-1.5">
            {Object.keys(ruleScores).length === 0 && (
              <div className="font-mono text-[11px] text-slate-600">no rules fired</div>
            )}
            {Object.entries(ruleScores).map(([k, v]) => (
              <div
                key={k}
                className="flex items-center justify-between rounded border border-slate-800 bg-slate-950/40 px-2.5 py-1.5"
              >
                <span className="font-mono text-[11px] text-slate-300">
                  {RULE_LABELS[k] || k}
                </span>
                <span className="font-mono text-xs font-semibold text-amber-400">{v}</span>
              </div>
            ))}
          </div>

          <div className="mt-3 mb-2 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
            <Boxes className="h-3 w-3" /> Cluster Groupings
          </div>
          {clusters.length === 0 && (
            <div className="font-mono text-[11px] text-slate-600">no clusters</div>
          )}
          {clusters.map((c) => (
            <div
              key={c.cluster_id}
              className="rounded border border-slate-800 bg-slate-950/40 px-2.5 py-1.5"
            >
              <span className="font-mono text-[11px] text-cyan-400">cluster #{c.cluster_id}</span>
              <span className="ml-2 font-mono text-[10px] text-slate-500">
                {c.event_count} event(s) · {c.distinct_signal_families} families
              </span>
            </div>
          ))}
        </div>

        {/* Provenance + raw payload */}
        <div>
          <div className="mb-2 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
            Traceability
          </div>
          <dl className="space-y-1 rounded border border-slate-800 bg-slate-950/40 p-2.5">
            <Trace label="event_id" value={target.event_id} />
            <Trace label="timestamp_utc" value={target.timestamp_utc} />
            <Trace label="origin_ts (raw)" value={target.timestamp_original} />
            <Trace
              label="baseline"
              value={`${(ev.baseline_event_ids || []).length} prior events`}
            />
            <Trace
              label="window"
              value={`${(ev.baseline_window?.from || "").slice(0, 10)} → ${(ev.baseline_window?.to || "").slice(0, 10)}`}
            />
          </dl>

          <div className="mt-3 mb-2 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
            <ShieldQuestion className="h-3 w-3" /> Untrusted Payload (rendered inert)
          </div>
          {/* React escapes text nodes, so these strings can never execute. */}
          <pre className="max-h-40 overflow-auto rounded border border-slate-800 bg-black/40 p-2.5 font-mono text-[10px] leading-relaxed text-slate-400">
            {JSON.stringify(
              {
                event_id: target.event_id,
                city: target.location?.city,
                country: target.location?.country,
                resource_family: target.resource_family,
                data_mb: target.data_mb,
                file_count: target.file_count,
              },
              null,
              2
            )}
          </pre>
        </div>
      </div>
    </div>
  );
}

function Trace({ label, value }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <dt className="font-mono text-[10px] text-slate-500">{label}</dt>
      <dd className="truncate font-mono text-[11px] text-slate-300">{value ?? "\u2014"}</dd>
    </div>
  );
}
