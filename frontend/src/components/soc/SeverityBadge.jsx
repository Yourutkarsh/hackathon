import { sevOf } from "@/lib/severity";
import { cn } from "@/lib/utils";

export function SeverityBadge({ severity, pulse = false, className }) {
  const s = sevOf(severity);
  return (
    <span
      data-testid="severity-badge"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2.5 py-1 font-mono text-[11px] font-semibold uppercase tracking-[0.15em]",
        s.badge,
        pulse && severity === "CRITICAL" && "animate-pulse-glow",
        className
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", s.dot)} />
      {s.label}
    </span>
  );
}
