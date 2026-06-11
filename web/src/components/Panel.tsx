import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type PanelState = "idle" | "running" | "done" | "failed";

const dot: Record<PanelState, string> = {
  idle: "var(--text-dim)",
  running: "var(--accent)",
  done: "var(--ok)",
  failed: "var(--danger)",
};

/**
 * One tile in the command-center grid. Carries a step label, a status dot, and
 * an optional right-aligned badge (latency, a verdict). Dims until its step has
 * produced something, so the grid reads as a console filling in live.
 */
export function Panel({
  title,
  state = "idle",
  badge,
  className,
  children,
}: {
  title: string;
  state?: PanelState;
  badge?: ReactNode;
  className?: string;
  children?: ReactNode;
}) {
  const empty = state === "idle";
  return (
    <section
      className={cn(
        "flex flex-col rounded-lg border transition-opacity",
        empty && "opacity-45",
        className,
      )}
      style={{ background: "var(--surface)", borderColor: "var(--border)" }}
    >
      <header className="flex items-center gap-2 border-b px-4 py-2.5" style={{ borderColor: "var(--border)" }}>
        <span
          className={cn("h-2 w-2 shrink-0 rounded-full", state === "running" && "animate-pulse")}
          style={{ background: dot[state] }}
        />
        <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
          {title}
        </span>
        {badge != null && <span className="ml-auto text-xs">{badge}</span>}
      </header>
      <div className="flex min-h-0 flex-1 flex-col p-4">{children}</div>
    </section>
  );
}
