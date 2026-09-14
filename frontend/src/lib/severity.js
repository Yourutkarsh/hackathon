// Severity semantics + component metadata. Display-only: never used to compute risk.

export const SEVERITY = {
  NORMAL: {
    label: "Normal",
    text: "text-slate-300",
    badge: "bg-slate-800/70 text-slate-300 border-slate-600/40",
    ring: "#64748B",
    dot: "bg-slate-400",
  },
  WATCH: {
    label: "Watch",
    text: "text-emerald-400",
    badge: "bg-emerald-950/60 text-emerald-400 border-emerald-500/30",
    ring: "#10B981",
    dot: "bg-emerald-400",
  },
  ELEVATED: {
    label: "Elevated",
    text: "text-amber-400",
    badge: "bg-amber-950/60 text-amber-400 border-amber-500/30",
    ring: "#F59E0B",
    dot: "bg-amber-400",
  },
  HIGH: {
    label: "High",
    text: "text-orange-400",
    badge: "bg-orange-950/60 text-orange-400 border-orange-500/30",
    ring: "#F97316",
    dot: "bg-orange-400",
  },
  CRITICAL: {
    label: "Critical",
    text: "text-rose-400",
    badge: "bg-rose-950/80 text-rose-400 border-rose-500/40",
    ring: "#EF4444",
    dot: "bg-rose-400",
  },
};

export const sevOf = (s) => SEVERITY[s] || SEVERITY.NORMAL;

export const SEVERITY_ORDER = ["WATCH", "ELEVATED", "HIGH", "CRITICAL"];

// Baseline lifecycle states (V5.1). Display-only metadata; the backend is
// authoritative for the state itself.
export const BASELINE_STATES = {
  COLD: {
    label: "Cold",
    hint: "< 20 trusted events — too little history to trust the baseline",
    badge: "bg-slate-800/70 text-slate-300 border-slate-600/40",
    dot: "bg-slate-400",
  },
  WARMING: {
    label: "Warming",
    hint: "building history — needs 50 events and 7 distinct days for READY",
    badge: "bg-amber-950/60 text-amber-400 border-amber-500/30",
    dot: "bg-amber-400",
  },
  READY: {
    label: "Ready",
    hint: "≥ 50 events across ≥ 7 distinct days",
    badge: "bg-emerald-950/60 text-emerald-400 border-emerald-500/30",
    dot: "bg-emerald-400",
  },
};

export const baselineOf = (s) => BASELINE_STATES[s] || BASELINE_STATES.COLD;

// Strict spec detection = HIGH/CRITICAL (70+). ELEVATED+ is the legacy alias.
export const SPEC_DETECTION_SEVERITIES = ["HIGH", "CRITICAL"];
export const LEGACY_DETECTION_SEVERITIES = ["ELEVATED", "HIGH", "CRITICAL"];

export const COMPONENTS = [
  { key: "behavioral_anomaly", label: "Behavioral Anomaly", sign: "+" },
  { key: "temporal_correlation", label: "Temporal Correlation", sign: "+" },
  { key: "sensitivity", label: "Sensitivity Elevation", sign: "+" },
  { key: "novelty", label: "Novelty", sign: "+" },
  { key: "context_adjustment", label: "Context Adjustment", sign: "\u2212" },
];

export const fmtNum = (n, d = 2) =>
  typeof n === "number" ? n.toFixed(d) : "\u2014";
