"use client";

import type { TrustComponents } from "@/lib/stream";

// The trust score and the three signals that compose it. The arc is the headline
// number; the bars below show what it's made of and how each is weighted, so the
// score is legible rather than a black box.

const WEIGHTS: Record<keyof TrustComponents, number> = {
  retrieval: 0.3,
  grounding: 0.4,
  decisiveness: 0.3,
};

const LABELS: Record<keyof TrustComponents, string> = {
  retrieval: "Retrieval",
  grounding: "Grounding",
  decisiveness: "Decisiveness",
};

function color(t: number): string {
  return t >= 0.6 ? "var(--ok)" : t >= 0.35 ? "var(--warn)" : "var(--danger)";
}

function Arc({ value }: { value: number }) {
  const r = 52;
  const c = Math.PI * r; // semicircle length
  const filled = Math.max(0, Math.min(1, value)) * c;
  return (
    <svg viewBox="0 0 140 78" className="w-full" style={{ maxWidth: 180 }}>
      <path d="M 18 70 A 52 52 0 0 1 122 70" fill="none" stroke="var(--surface-2)" strokeWidth={10} strokeLinecap="round" />
      <path
        d="M 18 70 A 52 52 0 0 1 122 70"
        fill="none"
        stroke={color(value)}
        strokeWidth={10}
        strokeLinecap="round"
        strokeDasharray={`${filled} ${c}`}
        style={{ transition: "stroke-dasharray 600ms ease, stroke 300ms" }}
      />
      <text x="70" y="60" textAnchor="middle" className="tabular-nums" style={{ fill: "var(--text)", fontSize: 30, fontWeight: 600 }}>
        {Math.round(value * 100)}
      </text>
      <text x="70" y="74" textAnchor="middle" style={{ fill: "var(--text-dim)", fontSize: 9, letterSpacing: 1 }}>
        / 100 TRUST
      </text>
    </svg>
  );
}

export function TrustGauge({
  trust,
  components,
  state,
  capped,
}: {
  trust: number;
  components: TrustComponents;
  state?: string;
  capped?: boolean;
}) {
  const keys = Object.keys(components) as (keyof TrustComponents)[];
  return (
    <div className="flex flex-col gap-3">
      <Arc value={trust} />

      <div className="flex flex-col gap-2">
        {keys.map((k) => {
          const v = components[k];
          return (
            <div key={k} className="flex items-center gap-2 text-[11px]">
              <span className="w-20 shrink-0" style={{ color: "var(--text-dim)" }}>
                {LABELS[k]}
              </span>
              <div className="h-1.5 flex-1 overflow-hidden rounded-full" style={{ background: "var(--surface-2)" }}>
                <div
                  className="h-full rounded-full"
                  style={{ width: `${Math.round(v * 100)}%`, background: color(v), transition: "width 500ms ease" }}
                />
              </div>
              <span className="w-7 shrink-0 text-right tabular-nums" style={{ color: "var(--text)" }}>
                {v.toFixed(2)}
              </span>
              <span className="w-8 shrink-0 text-right tabular-nums" style={{ color: "var(--text-dim)" }}>
                ×{WEIGHTS[k]}
              </span>
            </div>
          );
        })}
      </div>

      {(state || capped) && (
        <div className="text-[11px]" style={{ color: capped ? "var(--warn)" : "var(--text-dim)" }}>
          {capped
            ? "Score capped: some lesson claims read as ungrounded — provisional, not full confidence."
            : state === "weak_evidence"
              ? "Weak evidence — below the trust floor. Escalate to a human."
              : "Above the trust floor."}
        </div>
      )}
    </div>
  );
}
