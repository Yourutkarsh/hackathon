import { useState, useRef, useEffect } from "react";
import { Bot, Send, Sparkles, BookText, HelpCircle, ListChecks, Quote, Tag } from "lucide-react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { api } from "@/lib/api";

const QUICK = [
  "Why was this event flagged?",
  "What evidence is uncertain?",
  "What should I do next?",
];

function Section({ icon: Icon, title, items, color }) {
  if (!items || items.length === 0) return null;
  return (
    <div className="mt-2.5">
      <div className={`mb-1 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] ${color}`}>
        <Icon className="h-3 w-3" /> {title}
      </div>
      <ul className="space-y-1">
        {items.map((it, i) => (
          <li key={i} className="flex gap-1.5 font-body text-[12px] leading-relaxed text-slate-300">
            <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-slate-600" />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function AssistantDrawer({ open, onOpenChange, userId, eventId, onSent }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text) => {
    const q = (text ?? input).trim();
    if (!q || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);
    try {
      const res = await api.assistant(userId, q, eventId);
      setMessages((m) => [...m, { role: "assistant", data: res }]);
      onSent?.();
    } catch (e) {
      setMessages((m) => [
        ...m,
        { role: "assistant", data: { answer: "Assistant request failed.", citations: [] } },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="flex w-full flex-col border-slate-800 bg-[#0B1019] p-0 text-slate-100 sm:max-w-md"
      >
        <SheetHeader className="border-b border-slate-800 p-4">
          <SheetTitle className="flex items-center gap-2 font-heading text-white">
            <div className="grid h-7 w-7 place-items-center rounded-md border border-cyan-500/30 bg-cyan-500/10">
              <Bot className="h-4 w-4 text-cyan-400" />
            </div>
            Evidence Assistant
            <span className="ml-auto rounded border border-emerald-500/30 bg-emerald-950/40 px-1.5 py-0.5 font-mono text-[9px] uppercase text-emerald-400">
              offline · grounded
            </span>
          </SheetTitle>
        </SheetHeader>

        <ScrollArea className="flex-1 px-4">
          <div className="py-4">
            {messages.length === 0 && (
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
                <div className="flex items-center gap-1.5 text-cyan-400">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span className="font-mono text-[11px] uppercase tracking-wider">
                    grounded in current event
                  </span>
                </div>
                <p className="mt-2 font-body text-xs leading-relaxed text-slate-400">
                  Ask about the selected event. Answers are deterministic, cite event fields, and
                  never call an external model.
                </p>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className="mt-3 flex justify-end">
                  <div className="max-w-[85%] rounded-lg rounded-br-sm border border-cyan-500/30 bg-cyan-950/30 px-3 py-2 font-body text-[12px] text-cyan-100">
                    {m.text}
                  </div>
                </div>
              ) : (
                <div
                  key={i}
                  data-testid="assistant-message"
                  className="mt-3 rounded-lg rounded-bl-sm border border-slate-800 bg-slate-900/50 px-3 py-2.5"
                >
                  <p className="font-body text-[12px] leading-relaxed text-slate-200">
                    {m.data.answer}
                  </p>
                  <Section icon={BookText} title="Key Facts" items={m.data.key_facts} color="text-cyan-400" />
                  <Section icon={HelpCircle} title="Uncertainties" items={m.data.uncertainties} color="text-amber-400" />
                  <Section
                    icon={ListChecks}
                    title="Recommended Investigation Steps"
                    items={m.data.recommended_investigation_steps || m.data.recommended_steps}
                    color="text-emerald-400"
                  />
                  {(m.data.signal_families?.length > 0 ||
                    m.data.evidence_ids?.length > 0 ||
                    m.data.baseline_state) && (
                    <div className="mt-2.5">
                      <div className="mb-1 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
                        <Tag className="h-3 w-3" /> Grounded Evidence
                      </div>
                      <div className="flex flex-wrap items-center gap-1">
                        {m.data.baseline_state && (
                          <span className="rounded border border-cyan-500/30 bg-cyan-950/30 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-300">
                            baseline {m.data.baseline_state}
                          </span>
                        )}
                        {m.data.iforest && (
                          <span className="rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-slate-400">
                            iforest {m.data.iforest.available ? m.data.iforest.source : "unavailable"}
                          </span>
                        )}
                        {(m.data.signal_families || []).map((f) => (
                          <span
                            key={f}
                            className="rounded border border-amber-500/30 bg-amber-950/40 px-1.5 py-0.5 font-mono text-[9px] text-amber-300"
                          >
                            {f}
                          </span>
                        ))}
                        {(m.data.evidence_ids || []).map((id) => (
                          <span
                            key={id}
                            className="rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 font-mono text-[9px] text-slate-400"
                          >
                            {id}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {m.data.citations?.length > 0 && (
                    <div className="mt-2.5">
                      <div className="mb-1 flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.18em] text-slate-500">
                        <Quote className="h-3 w-3" /> Citations
                      </div>
                      <div className="flex flex-wrap gap-1">
                        {m.data.citations.map((c, ci) => (
                          <span
                            key={ci}
                            className="rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 font-mono text-[9px] text-slate-400"
                          >
                            {c.event_id}·{c.field}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                  {m.data.disclaimer && (
                    <div className="mt-2 font-mono text-[9px] text-slate-600">{m.data.disclaimer}</div>
                  )}
                </div>
              )
            )}
            {loading && (
              <div className="mt-3 font-mono text-[11px] text-slate-500">analyzing evidence…</div>
            )}
            <div ref={endRef} />
          </div>
        </ScrollArea>

        <div className="border-t border-slate-800 p-3">
          <div className="mb-2 flex flex-wrap gap-1.5">
            {QUICK.map((q) => (
              <button
                key={q}
                onClick={() => send(q)}
                disabled={loading}
                className="rounded-full border border-slate-700 bg-slate-900/60 px-2.5 py-1 font-body text-[11px] text-slate-400 transition-colors hover:border-cyan-500/40 hover:text-cyan-300"
              >
                {q}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <Input
              data-testid="assistant-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && send()}
              placeholder="Ask the evidence assistant…"
              className="border-slate-700 bg-slate-950/60 font-body text-sm text-slate-200"
            />
            <Button
              data-testid="assistant-send-button"
              onClick={() => send()}
              disabled={loading}
              className="bg-cyan-500 text-slate-950 hover:bg-cyan-400"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
