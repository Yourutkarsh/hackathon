import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { Bot, MapPin, Clock, User as UserIcon, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { sevOf } from "@/lib/severity";
import { Header } from "./Header";
import { OverviewStats } from "./OverviewStats";
import { EventStepper } from "./EventStepper";
import { BaselineContrast } from "./BaselineContrast";
import { ScoreDecomposition } from "./ScoreDecomposition";
import { EvidenceProvenance } from "./EvidenceProvenance";
import { ContextInspector } from "./ContextInspector";
import { AnalystActions } from "./AnalystActions";
import { AuditTrail } from "./AuditTrail";
import { AssistantDrawer } from "./AssistantDrawer";
import { EvaluationPanel } from "./EvaluationPanel";

const DEFAULT_USER = "rahul-006";
const HERO_EVENT = "rahul-006-e6";

export function SocWorkspace() {
  const [health, setHealth] = useState(null);
  const [users, setUsers] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState(DEFAULT_USER);
  const [userDetail, setUserDetail] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [investigation, setInvestigation] = useState(null);
  const [selectedEventId, setSelectedEventId] = useState(HERO_EVENT);
  const [demo, setDemo] = useState(null);
  const [revealed, setRevealed] = useState([]);
  const [audit, setAudit] = useState([]);
  const [busy, setBusy] = useState(false);
  const [booting, setBooting] = useState(true);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [transitioned, setTransitioned] = useState(false);
  const bootedRef = useRef(false);

  useEffect(() => {
    document.documentElement.classList.add("dark");
  }, []);

  const refreshAudit = useCallback(async () => {
    try {
      const a = await api.audit();
      setAudit(a.records || []);
    } catch (e) {
      /* non-fatal */
    }
  }, []);

  const loadUserContext = useCallback(async (userId, eventId) => {
    const [detail, tl] = await Promise.all([api.user(userId), api.timeline(userId)]);
    setUserDetail(detail);
    setTimeline(tl.events || []);
    const targetEvent =
      eventId ||
      (tl.events || []).find((e) => !e.quarantined && e.event_id === HERO_EVENT)?.event_id ||
      null;
    const inv = await api.investigate(userId, targetEvent);
    setInvestigation(inv);
    setSelectedEventId(inv.event_id);
  }, []);

  const boot = useCallback(async () => {
    setBooting(true);
    try {
      await api.reset();
      const [h, us] = await Promise.all([api.health(), api.users()]);
      setHealth(h);
      setUsers(us);
      setDemo({ cursor: h.demo_cursor ?? 0, total: 0, done: false });
      setSelectedUserId(DEFAULT_USER);
      await loadUserContext(DEFAULT_USER, HERO_EVENT);
      setRevealed([]);
      await refreshAudit();
    } catch (e) {
      toast.error("Backend unavailable", { description: "Could not reach the Sentinel API." });
    } finally {
      setBooting(false);
    }
  }, [loadUserContext, refreshAudit]);

  useEffect(() => {
    if (bootedRef.current) return;
    bootedRef.current = true;
    boot();
  }, [boot]);

  const handleReset = async () => {
    setBusy(true);
    try {
      const r = await api.reset();
      setDemo({ cursor: 0, total: r.document_counts?.events ?? 0, done: false, paused: false });
      setRevealed([]);
      setTransitioned(false);
      setSelectedUserId(DEFAULT_USER);
      await loadUserContext(DEFAULT_USER, HERO_EVENT);
      await refreshAudit();
      toast.success("Demo reset", {
        description: `Reseeded in ${r.reset_duration_ms}ms · hash ${r.fixture_hash.slice(0, 8)}`,
      });
    } catch (e) {
      toast.error("Reset failed");
    } finally {
      setBusy(false);
    }
  };

  const handleNext = async (force = false) => {
    setBusy(true);
    try {
      const r = await api.nextEvent(force);
      if (r.paused) {
        setDemo((d) => ({ ...(d || {}), paused: true }));
        toast.info("Paused at the London anomaly", {
          description: "Review the compound anomaly, then press Resume to continue the stream.",
        });
        return;
      }
      if (r.done) {
        setDemo((d) => ({ ...(d || {}), done: true, paused: false, cursor: r.cursor, total: r.total }));
        toast.info("Event stream complete");
        return;
      }
      const ev = r.revealed_event;
      setDemo({ cursor: r.cursor, total: r.total, done: false, paused: false });
      setRevealed((prev) => [...prev, ev]);
      setSelectedUserId(ev.user_id);
      setSelectedEventId(ev.event_id);
      setInvestigation(ev);
      const [detail, tl] = await Promise.all([api.user(ev.user_id), api.timeline(ev.user_id)]);
      setUserDetail(detail);
      setTimeline(tl.events || []);
      const flagged = ["ELEVATED", "HIGH", "CRITICAL"].includes(ev.severity);
      if (flagged) {
        setTransitioned(true);
        setTimeout(() => setTransitioned(false), 2500);
        toast.warning(`${sevOf(ev.severity).label} anomaly · ${ev.display_name}`, {
          description: `${ev.event_id} scored ${ev.risk_score} from ${ev.evidence?.target_event?.location?.city}`,
        });
      }
      await refreshAudit();
    } catch (e) {
      toast.error("Step failed");
    } finally {
      setBusy(false);
    }
  };

  const handleSelectUser = async (userId) => {
    setSelectedUserId(userId);
    setBusy(true);
    try {
      await loadUserContext(userId, null);
    } catch (e) {
      toast.error("Could not load user");
    } finally {
      setBusy(false);
    }
  };

  const handleSelectEvent = async (ev) => {
    if (ev.quarantined) {
      toast.error("Quarantined event", {
        description: `${ev.event_id} excluded from trusted scoring · ${(ev.quarantine_reasons || []).join(", ")}`,
      });
      return;
    }
    setBusy(true);
    try {
      const inv = await api.investigate(selectedUserId, ev.event_id);
      setInvestigation(inv);
      setSelectedEventId(ev.event_id);
      await refreshAudit();
    } catch (e) {
      toast.error("Investigation failed");
    } finally {
      setBusy(false);
    }
  };

  const handleAction = async (action, note) => {
    if (!investigation) return;
    setBusy(true);
    try {
      const res = await api.action({
        user_id: selectedUserId,
        event_id: investigation.event_id,
        action,
        note,
      });
      await refreshAudit();
      const label = { NOTE: "Note appended", ESCALATE: "Escalated", DISMISS: "Dismissed" }[action];
      toast.success(label, {
        description: `Audit appended · risk unchanged at ${res.risk_score_unchanged} (${res.severity_unchanged})`,
      });
    } catch (e) {
      toast.error("Action failed");
    } finally {
      setBusy(false);
    }
  };

  const revealedMap = revealed.reduce((acc, r) => {
    acc[r.event_id] = r.severity;
    return acc;
  }, {});

  const topDrift = Object.values(
    revealed.reduce((acc, r) => {
      const cur = acc[r.user_id];
      if (!cur || r.risk_score > cur.risk_score) {
        acc[r.user_id] = {
          user_id: r.user_id,
          name: r.display_name || r.user_id,
          risk_score: r.risk_score,
          severity: r.severity,
        };
      }
      return acc;
    }, {})
  ).sort((a, b) => b.risk_score - a.risk_score);

  if (booting) {
    return (
      <div className="grid min-h-screen place-items-center bg-[#090D14]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-6 w-6 animate-spin text-cyan-400" />
          <span className="font-mono text-xs uppercase tracking-[0.3em] text-slate-500">
            initializing SOC…
          </span>
        </div>
      </div>
    );
  }

  const sev = sevOf(investigation?.severity);

  return (
    <div className="min-h-screen bg-[#090D14] font-body text-slate-200">
      <Header
        health={health}
        users={users}
        selectedUserId={selectedUserId}
        onSelectUser={handleSelectUser}
        onReset={handleReset}
        onNext={handleNext}
        demo={demo}
        investigation={investigation}
        busy={busy}
        transitioned={transitioned}
      />

      <main className="mx-auto max-w-[1800px] space-y-4 px-4 py-5 sm:px-6">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-500">
            SOC Overview · {users.length} monitored users
          </div>
          <EvaluationPanel />
        </div>

        <OverviewStats
          revealed={revealed}
          topDrift={topDrift}
          confidence={investigation?.confidence}
        />

        <EventStepper
          events={timeline}
          selectedEventId={selectedEventId}
          revealedMap={revealedMap}
          onSelect={handleSelectEvent}
        />

        {/* Subject banner */}
        <div
          className="flex flex-wrap items-center gap-3 rounded-lg border p-4"
          style={{ borderColor: `${sev.ring}40`, background: `${sev.ring}0d` }}
        >
          <div className="grid h-10 w-10 place-items-center rounded-md border border-slate-700 bg-slate-900">
            <UserIcon className="h-5 w-5 text-slate-300" />
          </div>
          <div>
            <div className="font-heading text-lg font-bold text-white">
              {userDetail?.display_name || selectedUserId}
            </div>
            <div className="flex items-center gap-3 font-mono text-[11px] text-slate-400">
              <span className="flex items-center gap-1">
                <MapPin className="h-3 w-3" /> {investigation?.evidence?.target_event?.location?.city}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />{" "}
                {(investigation?.evidence?.target_event?.timestamp_original || "").replace("T", " ")}
              </span>
              <span>{selectedEventId}</span>
            </div>
          </div>
          <div className="ml-auto text-right">
            <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-slate-500">
              engine risk
            </div>
            <div className={`font-heading text-3xl font-extrabold ${sev.text}`}>
              {investigation ? investigation.risk_score.toFixed(2) : "\u2014"}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <BaselineContrast investigation={investigation} user={userDetail} />
          <ScoreDecomposition investigation={investigation} />
        </div>

        <EvidenceProvenance investigation={investigation} />

        <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <ContextInspector investigation={investigation} />
          <div className="space-y-4">
            <AnalystActions onAction={handleAction} busy={busy} disabled={!investigation} />
            <AuditTrail records={audit} />
          </div>
        </div>
      </main>

      {/* Floating assistant toggle */}
      <button
        data-testid="assistant-drawer-toggle"
        onClick={() => setAssistantOpen(true)}
        className="fixed bottom-6 right-6 z-40 flex items-center gap-2 rounded-full border border-cyan-500/40 bg-cyan-500 px-4 py-3 font-heading text-sm font-semibold text-slate-950 shadow-lg shadow-cyan-500/20 transition-transform duration-200 hover:-translate-y-0.5 hover:bg-cyan-400"
      >
        <Bot className="h-4 w-4" /> Evidence Assistant
      </button>

      <AssistantDrawer
        open={assistantOpen}
        onOpenChange={setAssistantOpen}
        userId={selectedUserId}
        eventId={selectedEventId}
        onSent={refreshAudit}
      />
    </div>
  );
}
