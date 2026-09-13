import { useState } from "react";
import { FileText, ArrowUpCircle, XOctagon, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";

export function AnalystActions({ onAction, busy, disabled }) {
  const [noteOpen, setNoteOpen] = useState(false);
  const [note, setNote] = useState("");

  const submitNote = () => {
    onAction("NOTE", note.trim() || "(no text)");
    setNote("");
    setNoteOpen(false);
  };

  return (
    <div className="rounded-lg border border-white/[0.08] bg-slate-900/50 p-4">
      <div className="mb-3 flex items-center gap-2">
        <Lock className="h-3.5 w-3.5 text-cyan-400" />
        <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-slate-400">
          Analyst Action Dock
        </span>
        <span className="ml-auto rounded border border-slate-700 bg-slate-800/60 px-1.5 py-0.5 font-mono text-[9px] text-slate-500">
          append-only · non-destructive
        </span>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <Button
          data-testid="add-note-button"
          variant="outline"
          disabled={disabled}
          onClick={() => setNoteOpen(true)}
          className="border-slate-700 bg-slate-950/40 text-slate-200 hover:border-cyan-500/40 hover:text-white"
        >
          <FileText className="mr-1.5 h-4 w-4" /> Add Note
        </Button>
        <Button
          data-testid="escalate-button"
          disabled={disabled || busy}
          onClick={() => onAction("ESCALATE")}
          className="bg-orange-500 font-semibold text-slate-950 hover:bg-orange-400"
        >
          <ArrowUpCircle className="mr-1.5 h-4 w-4" /> Escalate
        </Button>
        <Button
          data-testid="dismiss-button"
          variant="outline"
          disabled={disabled || busy}
          onClick={() => onAction("DISMISS")}
          className="border-rose-500/30 bg-rose-950/20 text-rose-300 hover:border-rose-500/50 hover:text-rose-200"
        >
          <XOctagon className="mr-1.5 h-4 w-4" /> Dismiss
        </Button>
      </div>

      <Dialog open={noteOpen} onOpenChange={setNoteOpen}>
        <DialogContent className="border-slate-700 bg-slate-900 text-slate-100">
          <DialogHeader>
            <DialogTitle className="font-heading">Add Investigation Note</DialogTitle>
          </DialogHeader>
          <Textarea
            data-testid="analyst-note-input"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Document your reasoning… (appended to the audit trail, never alters the score)"
            className="min-h-[120px] border-slate-700 bg-slate-950/60 font-body text-sm text-slate-200"
          />
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setNoteOpen(false)}
              className="border-slate-700 bg-slate-950/40 text-slate-300"
            >
              Cancel
            </Button>
            <Button
              data-testid="save-note-button"
              onClick={submitNote}
              className="bg-cyan-500 font-semibold text-slate-950 hover:bg-cyan-400"
            >
              Append to Audit
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
