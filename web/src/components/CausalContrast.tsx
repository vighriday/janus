"use client";

import type { CausalEffect } from "@/lib/stream";

// The DoWhy do()-intervention result: holding everything else fixed, what moving
// the top-vendor dependency from high to low does to expected resilience loss.
// This is the literal counterfactual behind the recommendation — the thing that
// earns the word, distinct from the Monte-Carlo bands. The numbers come straight
// off the wire (sim/causal.py), not authored here.

function money(v: number): string {
  const a = Math.abs(v);
  const s = a >= 1e6 ? `${(a / 1e6).toFixed(2)}M` : a >= 1e3 ? `${Math.round(a / 1e3)}k` : `${Math.round(a)}`;
  return `$${s}`;
}

function pct(v: number): string {
  return `${Math.round(v * 100)}%`;
}

export function CausalContrast({ causal }: { causal: CausalEffect }) {
  const saved = causal.resilience_saved;
  // The expected, well-behaved case is that cutting dependency cuts loss (saved >
  // 0). Guard the copy on the sign so the sentence can never contradict the
  // numbers: if a fit ever inverted it, the verb and colour follow the data.
  const cuts = saved >= 0;
  return (
    <div className="flex flex-col gap-3">
      <div
        className="rounded-md border px-3 py-2.5"
        style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
      >
        <div className="text-[11px] uppercase tracking-wide" style={{ color: "var(--text-dim)" }}>
          do() intervention
        </div>
        <p className="mt-1 text-sm leading-relaxed" style={{ color: "var(--text)" }}>
          Holding everything else fixed, moving the top-vendor dependency from{" "}
          <span className="font-semibold tabular-nums" style={{ color: "var(--danger)" }}>
            {pct(causal.dependency_high)}
          </span>{" "}
          down to{" "}
          <span className="font-semibold tabular-nums" style={{ color: "var(--ok)" }}>
            {pct(causal.dependency_low)}
          </span>{" "}
          {cuts ? "cuts expected resilience loss by" : "raises expected resilience loss by"}{" "}
          <span
            className="font-semibold tabular-nums"
            style={{ color: cuts ? "var(--ok)" : "var(--danger)" }}
          >
            {money(saved)}
          </span>
          .
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-md border px-2.5 py-2" style={{ borderColor: "var(--border)" }}>
          <div style={{ color: "var(--text-dim)" }}>at {pct(causal.dependency_high)} dependency</div>
          <div className="mt-0.5 font-semibold tabular-nums" style={{ color: "var(--danger)" }}>
            {money(causal.resilience_loss_at_high)}
          </div>
        </div>
        <div className="rounded-md border px-2.5 py-2" style={{ borderColor: "var(--border)" }}>
          <div style={{ color: "var(--text-dim)" }}>at {pct(causal.dependency_low)} dependency</div>
          <div className="mt-0.5 font-semibold tabular-nums" style={{ color: "var(--ok)" }}>
            {money(causal.resilience_loss_at_low)}
          </div>
        </div>
      </div>
    </div>
  );
}
