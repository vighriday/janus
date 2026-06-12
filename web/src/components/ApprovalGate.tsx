"use client";

import { useState } from "react";
import type { FutureBand } from "@/lib/stream";
import { cn } from "@/lib/cn";
import { tidyLesson } from "@/lib/lesson";

// The human-in-the-loop gate. JANUS never executes — it recommends, and a person
// decides. The verdict and its justification come from the run itself: the
// grounded lesson and the recommended future's modelled outcome, not canned
// prose. The operator approves or overrides.

type Decision = "approved" | "overridden" | null;

const VERDICT_META: Record<string, { title: string; tone: string }> = {
  approve: { title: "Approve", tone: "var(--ok)" },
  modify: { title: "Modify", tone: "var(--warn)" },
  reject: { title: "Reject", tone: "var(--danger)" },
  review: { title: "Escalate", tone: "var(--text-dim)" },
};

function money(v: number): string {
  const a = Math.abs(v);
  const s = a >= 1e6 ? `${(a / 1e6).toFixed(2)}M` : a >= 1e3 ? `${Math.round(a / 1e3)}k` : `${Math.round(a)}`;
  return v < 0 ? `-$${s}` : `$${s}`;
}

export function ApprovalGate({
  recommended,
  lesson,
  futures,
  awaiting,
  onDecide,
}: {
  recommended: string;
  lesson?: string;
  futures?: FutureBand[];
  awaiting?: boolean;
  onDecide?: (approved: boolean) => void;
}) {
  const [decision, setDecision] = useState<Decision>(null);
  const meta = VERDICT_META[recommended] ?? VERDICT_META.review;
  const rec = futures?.find((f) => f.label === recommended);
  // The justification is the grounded lesson (first sentence, cleaned of markdown
  // and prompt-echo) plus the recommended future's own modelled median — both
  // produced by the run, not authored here.
  const lessonLead = lesson ? tidyLesson(lesson).split(/(?<=\.)\s/)[0] : "";

  // When the workflow is paused server-side (awaiting), the buttons resume the
  // real run over the wire; the decision is resolved by the backend, not faked
  // in local state.
  const choose = (d: Exclude<Decision, null>) => {
    setDecision(d);
    onDecide?.(d === "approved");
  };

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="text-[11px] uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
          Recommended
        </span>
        <span
          className="rounded px-2 py-0.5 text-xs font-semibold uppercase tracking-wide"
          style={{ background: meta.tone, color: "#0a0a0b" }}
        >
          {meta.title}
        </span>
      </div>

      {lessonLead && (
        <p className="text-xs leading-relaxed" style={{ color: "var(--text-dim)" }}>
          {lessonLead}
        </p>
      )}
      {rec && (
        <p className="text-xs" style={{ color: "var(--text-dim)" }}>
          The recommended <span style={{ color: "var(--text)" }}>{recommended}</span> future
          models a median of{" "}
          <span className="tabular-nums font-medium" style={{ color: "var(--text)" }}>
            {money(rec.p50)}
          </span>{" "}
          at <span className="tabular-nums">{rec.risk_label}</span> risk.
        </p>
      )}

      {decision == null ? (
        <div className="flex gap-2">
          <button
            onClick={() => choose("approved")}
            disabled={!awaiting}
            className="flex-1 rounded-md px-3 py-2 text-xs font-semibold transition disabled:opacity-50"
            style={{ background: "var(--ok)", color: "#0a0a0b" }}
          >
            Approve recommendation
          </button>
          <button
            onClick={() => choose("overridden")}
            disabled={!awaiting}
            className="flex-1 rounded-md border px-3 py-2 text-xs font-medium transition disabled:opacity-50"
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
            ? `Human approved the “${meta.title.toLowerCase()}” recommendation. The workflow resumed and recorded it.`
            : "Human overrode the recommendation. The workflow resumed and logged it — nothing executed."}
        </div>
      )}

      <div className="text-[10px]" style={{ color: "var(--text-dim)" }}>
        JANUS is decision-support. It never executes an action on its own.
      </div>
    </div>
  );
}
