"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";

// The human-in-the-loop gate. JANUS never executes — it recommends, and a person
// decides. The recommended verdict is surfaced with its reasoning; the operator
// approves or overrides. The decision is recorded locally for the demo.

type Decision = "approved" | "overridden" | null;

const VERDICT_COPY: Record<string, { title: string; tone: string; why: string }> = {
  approve: {
    title: "Approve",
    tone: "var(--ok)",
    why: "Below the 70% concentration knee the savings dominate and the resilience tail stays survivable.",
  },
  modify: {
    title: "Modify",
    tone: "var(--warn)",
    why: "Full consolidation crosses the concentration knee; cap the top vendor and keep a warm fallback.",
  },
  reject: {
    title: "Reject",
    tone: "var(--danger)",
    why: "Every modelled future carries a catastrophic downside — hold the status quo.",
  },
  review: {
    title: "Escalate",
    tone: "var(--text-dim)",
    why: "Evidence is too thin to recommend — a human should decide.",
  },
};

export function ApprovalGate({ recommended }: { recommended: string }) {
  const [decision, setDecision] = useState<Decision>(null);
  const copy = VERDICT_COPY[recommended] ?? VERDICT_COPY.review;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
          Recommended
        </span>
        <span
          className="rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide"
          style={{ background: copy.tone, color: recommended === "modify" ? "#1a1a1a" : "white" }}
        >
          {copy.title}
        </span>
      </div>
      <p className="text-xs leading-relaxed" style={{ color: "var(--text-dim)" }}>
        {copy.why}
      </p>

      {decision == null ? (
        <div className="flex gap-2">
          <button
            onClick={() => setDecision("approved")}
            className="flex-1 rounded-md px-3 py-2 text-xs font-medium text-white transition"
            style={{ background: "var(--ok)" }}
          >
            Approve recommendation
          </button>
          <button
            onClick={() => setDecision("overridden")}
            className="flex-1 rounded-md border px-3 py-2 text-xs font-medium transition"
            style={{ borderColor: "var(--border)", color: "var(--text)" }}
          >
            Override
          </button>
        </div>
      ) : (
        <div
          className={cn("rounded-md border px-3 py-2 text-xs")}
          style={{
            borderColor: decision === "approved" ? "var(--ok)" : "var(--warn)",
            color: "var(--text)",
            background: "var(--surface-2)",
          }}
        >
          {decision === "approved"
            ? `Human approved the “${copy.title.toLowerCase()}” recommendation. Action released for execution.`
            : "Human overrode the recommendation. Logged for review — nothing executed."}
          <button onClick={() => setDecision(null)} className="ml-2 underline" style={{ color: "var(--text-dim)" }}>
            reset
          </button>
        </div>
      )}

      <div className="text-[10px]" style={{ color: "var(--text-dim)" }}>
        JANUS is decision-support. It never executes an action on its own.
      </div>
    </div>
  );
}
