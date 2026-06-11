"use client";

import { cn } from "@/lib/cn";

// The intercepted action and the one lever the operator can move: how much of
// the critical flow ends up on the top vendor. Drag it across the 70%
// concentration knee and re-run — the recommendation flips, because the
// simulation actually reads this number.

export function ActionBar({
  dependency,
  onDependency,
  running,
  onRun,
  contractValue,
}: {
  dependency: number;
  onDependency: (v: number) => void;
  running: boolean;
  onRun: () => void;
  contractValue: number;
}) {
  const pct = Math.round(dependency * 100);
  const overKnee = dependency > 0.7;

  return (
    <div className="flex flex-col gap-4 rounded-lg border p-5 lg:flex-row lg:items-end lg:gap-8" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
      <div className="flex-1">
        <div className="text-[11px] uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
          Proposed action — intercepted
        </div>
        <div className="mt-1 text-sm" style={{ color: "var(--text)" }}>
          Auto-approve the{" "}
          <span className="tabular-nums font-medium">${(contractValue / 1e6).toFixed(2)}M</span>{" "}
          carrier-routing renewal and consolidate vendors onto Vendor X.
        </div>
      </div>

      <div className="lg:w-72">
        <div className="flex items-baseline justify-between text-[11px]">
          <span className="uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
            Top-vendor dependency
          </span>
          <span className="tabular-nums text-sm font-semibold" style={{ color: overKnee ? "var(--danger)" : "var(--ok)" }}>
            {pct}%
          </span>
        </div>
        <input
          type="range"
          min={40}
          max={100}
          step={5}
          value={pct}
          disabled={running}
          onChange={(e) => onDependency(Number(e.target.value) / 100)}
          className="mt-2 w-full accent-[var(--accent)] disabled:opacity-50"
        />
        <div className="mt-0.5 flex justify-between text-[10px]" style={{ color: "var(--text-dim)" }}>
          <span>40%</span>
          <span className={cn(overKnee && "font-semibold")} style={{ color: "var(--warn)" }}>70% knee</span>
          <span>100%</span>
        </div>
      </div>

      <button
        onClick={onRun}
        disabled={running}
        className="rounded-md px-5 py-2.5 text-sm font-medium text-white transition disabled:opacity-50"
        style={{ background: "var(--accent)" }}
      >
        {running ? "Running…" : "Run JANUS"}
      </button>
    </div>
  );
}
