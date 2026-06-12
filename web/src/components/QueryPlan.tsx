"use client";

// The subqueries Foundry IQ's planner generated for this retrieval. This is the
// distinctive "agentic" beat — the service decomposed one decision question into
// several searches, ran and reranked them. Rendering it is what separates this
// from a plain vector lookup, so it earns its own panel.

export function QueryPlan({ subqueries }: { subqueries: string[] }) {
  if (!subqueries.length) {
    return (
      <div className="text-xs" style={{ color: "var(--text-dim)" }}>
        The planner returned no separate subqueries for this question.
      </div>
    );
  }
  return (
    <ol className="flex flex-col gap-1.5">
      {subqueries.map((q, i) => (
        <li
          key={i}
          className="flex items-start gap-2 rounded-md border px-2.5 py-1.5 text-xs"
          style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
        >
          <span
            className="mt-px flex h-4 w-4 shrink-0 items-center justify-center rounded text-[10px] font-semibold tabular-nums"
            style={{ background: "var(--accent)", color: "white" }}
            aria-hidden="true"
          >
            {i + 1}
          </span>
          <span style={{ color: "var(--text)" }}>{q}</span>
        </li>
      ))}
    </ol>
  );
}
