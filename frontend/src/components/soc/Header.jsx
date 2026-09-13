import { Shield, RotateCcw, ChevronRight, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AnimatedScore } from "./AnimatedScore";
import { SeverityBadge } from "./SeverityBadge";
import { sevOf } from "@/lib/severity";

export function Header({
  health,
  users,
  selectedUserId,
  onSelectUser,
  onReset,
  onNext,
  demo,
  investigation,
  busy,
  transitioned,
}) {
  const sev = investigation?.severity;
  const s = sevOf(sev);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-800 bg-[#090D14]/90 backdrop-blur-md">
      <div className="mx-auto flex min-h-16 max-w-[1800px] flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2 sm:px-6">
        <div className="flex items-center gap-2.5">
          <div className="grid h-9 w-9 place-items-center rounded-md border border-cyan-500/30 bg-cyan-500/10">
            <Shield className="h-5 w-5 text-cyan-400" />
          </div>
          <div className="leading-tight">
            <div className="font-heading text-sm font-extrabold tracking-tight text-white">
              SENTINEL&nbsp;SHIFT
            </div>
            <div className="font-mono text-[10px] uppercase tracking-[0.25em] text-slate-500">
              v{health?.engine_version || "5.1"} · SOC
            </div>
          </div>
        </div>

        <div className="hidden items-center gap-1.5 md:flex">
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              health?.engine_integrity_ok ? "bg-emerald-400" : "bg-rose-400"
            }`}
          />
          <span className="font-mono text-[10px] uppercase tracking-wider text-slate-500">
            engine {health?.engine_integrity_ok ? "locked" : "tamper"}
          </span>
        </div>

        <div className="ml-auto flex flex-wrap items-center justify-end gap-2 sm:gap-3">
          <Select value={selectedUserId} onValueChange={onSelectUser}>
            <SelectTrigger
              data-testid="user-select-dropdown"
              className="h-9 w-[150px] border-slate-700 bg-slate-900/70 font-body text-xs text-slate-200 sm:w-[190px]"
            >
              <SelectValue placeholder="Select analyst subject" />
            </SelectTrigger>
            <SelectContent className="border-slate-700 bg-slate-900 text-slate-200">
              {users.map((u) => (
                <SelectItem key={u.user_id} value={u.user_id} className="text-xs">
                  {u.display_name} · {u.location?.city}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {investigation && (
            <div
              data-testid="risk-score-display"
              className="hidden items-center gap-2 rounded-md border px-3 py-1.5 sm:flex"
              style={{
                borderColor: `${s.ring}55`,
                background: `${s.ring}14`,
                boxShadow: transitioned ? `0 0 22px ${s.ring}66` : "none",
                transition: "box-shadow 400ms ease",
              }}
            >
              <Activity className="h-3.5 w-3.5" style={{ color: s.ring }} />
              <AnimatedScore
                value={investigation.risk_score}
                className="font-mono text-sm font-semibold"
              />
              <SeverityBadge severity={sev} pulse />
            </div>
          )}

          <Button
            data-testid="reset-demo-button"
            variant="outline"
            size="sm"
            disabled={busy}
            onClick={onReset}
            className="h-9 border-slate-700 bg-slate-900/70 text-slate-200 hover:border-cyan-500/40 hover:text-white"
          >
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Reset
          </Button>

          <Button
            data-testid="next-event-button"
            size="sm"
            disabled={busy || demo?.done}
            onClick={() => onNext(demo?.paused === true)}
            className={`h-9 font-semibold text-slate-950 ${
              demo?.paused ? "bg-amber-400 hover:bg-amber-300" : "bg-cyan-500 hover:bg-cyan-400"
            }`}
          >
            {demo?.done ? "Stream Complete" : demo?.paused ? "Resume Stream" : "Next Event"}
            {!demo?.done && <ChevronRight className="ml-1 h-4 w-4" />}
          </Button>

          <div className="hidden rounded-md border border-slate-700 bg-slate-900/70 px-2.5 py-1.5 font-mono text-[11px] text-slate-400 lg:block">
            {demo ? `${demo.cursor}/${demo.total}` : "0/0"}
          </div>
        </div>
      </div>
    </header>
  );
}
