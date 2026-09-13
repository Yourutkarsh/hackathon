import { Dna, Home, Plane, ArrowRight } from "lucide-react";

const minToHHMM = (m) => {
  if (m == null) return "\u2014";
  const h = String(Math.floor(m / 60)).padStart(2, "0");
  const mm = String(m % 60).padStart(2, "0");
  return `${h}:${mm}`;
};

function Row({ label, base, anom, flag }) {
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-md border border-slate-800">
      <div className="bg-slate-950/40 p-2.5">
        <div className="font-mono text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
        <div className="mt-0.5 font-mono text-xs text-slate-300">{base}</div>
      </div>
      <div className={`p-2.5 ${flag ? "bg-amber-950/30" : "bg-slate-950/40"}`}>
        <div className="font-mono text-[9px] uppercase tracking-wider text-slate-500">{label}</div>
        <div className={`mt-0.5 font-mono text-xs ${flag ? "text-amber-300" : "text-slate-300"}`}>
          {anom}
        </div>
      </div>
    </div>
  );
}

export function BaselineContrast({ investigation, user }) {
  const ev = investigation?.evidence?.target_event;
  if (!ev) return null;
  const baseCity = user?.location?.city || "\u2014";
  const baseCountry = user?.location?.country || "";
  const b = user?.baseline || {};
  const evCity = ev.location?.city || "\u2014";
  const evCountry = ev.location?.country || "";
  const locFlag = evCity !== baseCity;
  const localTime = (ev.timestamp_original || "").slice(11, 16) || "\u2014";
  const tzFlag = ev.user_timezone !== user?.user_timezone;

  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-5">
      <div className="mb-4 flex items-center gap-2">
        <Dna className="h-4 w-4 text-cyan-400" />
        <h3 className="font-heading text-base font-semibold text-white">
          Behavioral DNA &amp; Baseline Contrast
        </h3>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-3">
        <div className="rounded-md border border-emerald-500/20 bg-emerald-950/20 p-3">
          <div className="flex items-center gap-1.5 text-emerald-400">
            <Home className="h-3.5 w-3.5" />
            <span className="font-mono text-[10px] uppercase tracking-[0.2em]">Baseline</span>
          </div>
          <div className="mt-1.5 font-heading text-sm font-semibold text-white">
            {baseCity}
          </div>
          <div className="font-mono text-[11px] text-slate-400">{baseCountry}</div>
        </div>
        <div className="relative rounded-md border border-amber-500/30 bg-amber-950/20 p-3">
          <div className="flex items-center gap-1.5 text-amber-400">
            <Plane className="h-3.5 w-3.5" />
            <span className="font-mono text-[10px] uppercase tracking-[0.2em]">Observed</span>
          </div>
          <div className="mt-1.5 font-heading text-sm font-semibold text-white">{evCity}</div>
          <div className="font-mono text-[11px] text-amber-300/80">{evCountry}</div>
          {locFlag && (
            <ArrowRight className="absolute -left-3 top-1/2 hidden h-5 w-5 -translate-y-1/2 text-amber-400 sm:block" />
          )}
        </div>
      </div>

      <div className="space-y-2">
        <Row
          label="Active Hours"
          base={`${minToHHMM(b.active_start_minute)}–${minToHHMM(b.active_end_minute)}`}
          anom={`${localTime} local`}
          flag
        />
        <Row
          label="Timezone"
          base={user?.user_timezone || "\u2014"}
          anom={ev.user_timezone || "\u2014"}
          flag={tzFlag}
        />
        <Row
          label="Sensitivity"
          base="MEDIUM (typical)"
          anom={ev.sensitivity || "\u2014"}
          flag={ev.sensitivity === "HIGH" || ev.sensitivity === "CRITICAL"}
        />
        <Row
          label="Volume (MB)"
          base={`~${(b.data_mb_baseline || []).slice(-1)[0] ?? "\u2014"}`}
          anom={`${ev.data_mb ?? "\u2014"}`}
          flag={ev.data_mb != null && ev.data_mb > 100}
        />
      </div>
    </div>
  );
}
