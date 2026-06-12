"use client";

import type { FutureBand, RiskLabel } from "@/lib/stream";
import { cn } from "@/lib/cn";

const RISK_COLOR: Record<RiskLabel, string> = {
  low: "var(--ok)",
  elevated: "var(--warn)",
  high: "var(--danger)",
};

function money(v: number): string {
  const a = Math.abs(v);
  const s = a >= 1e6 ? `${(a / 1e6).toFixed(2)}M` : a >= 1e3 ? `${Math.round(a / 1e3)}k` : `${Math.round(a)}`;
  return v < 0 ? `-$${s}` : `$${s}`;
}

// A future's outcome range crosses zero (a bad P10 can be deeply negative while
// P90 is a modest gain), which the stacked-bar trick can't render. So we draw the
// bands ourselves: one shared linear scale across all three futures, a P10->P90
// range bar per future, a P50 marker, and a zero line. Pure SVG over a computed
// scale — no charting-library range gymnastics, and negatives just work.

const PAD_L = 64;
const PAD_R = 16;
const ROW_H = 34;
const GAP = 14;

export function FuturesChart({
  futures,
  recommended,
}: {
  futures: FutureBand[];
  recommended: string;
}) {
  const order = ["approve", "modify", "reject"];
  const rows = [...futures].sort((a, b) => order.indexOf(a.label) - order.indexOf(b.label));

  const lo = Math.min(0, ...rows.map((r) => r.p10));
  const hi = Math.max(0, ...rows.map((r) => r.p90));
  const span = hi - lo || 1;

  // ViewBox in abstract units; the SVG scales to the panel width.
  const W = 1000;
  const plotW = W - PAD_L - PAD_R;
  const H = rows.length * (ROW_H + GAP) + 24;
  const x = (v: number) => PAD_L + ((v - lo) / span) * plotW;

  const ticks = [lo, lo + span / 2, hi];

  const summary =
    "Outcome ranges per future. " +
    rows
      .map(
        (r) =>
          `${r.label}: median ${money(r.p50)}, range ${money(r.p10)} to ${money(r.p90)}, ${r.risk_label} risk${r.label === recommended ? ", recommended" : ""}`,
      )
      .join(". ") +
    ".";

  return (
    <div className="flex h-full flex-col">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        preserveAspectRatio="xMidYMid meet"
        style={{ maxHeight: 200 }}
        role="img"
        aria-label={summary}
      >
        {/* x grid + labels */}
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={x(t)} y1={6} x2={x(t)} y2={H - 18} stroke="var(--border)" strokeWidth={1} />
            <text x={x(t)} y={H - 4} textAnchor="middle" style={{ fill: "var(--text-dim)", fontSize: 12 }}>
              {money(t)}
            </text>
          </g>
        ))}
        {/* zero line */}
        <line x1={x(0)} y1={6} x2={x(0)} y2={H - 18} stroke="var(--text-dim)" strokeWidth={1.5} strokeDasharray="4 4" />

        {rows.map((r, i) => {
          const y = 8 + i * (ROW_H + GAP);
          const cy = y + ROW_H / 2;
          const rec = r.label === recommended;
          const color = RISK_COLOR[r.risk_label];
          const x10 = x(r.p10);
          const x90 = x(r.p90);
          const x50 = x(r.p50);
          return (
            <g key={r.label}>
              <text x={PAD_L - 10} y={cy + 4} textAnchor="end" style={{ fill: "var(--text)", fontSize: 13, fontWeight: rec ? 600 : 400 }}>
                {r.label.charAt(0).toUpperCase() + r.label.slice(1)}
              </text>
              {/* P10 -> P90 range */}
              <rect
                x={Math.min(x10, x90)}
                y={y + 6}
                width={Math.max(2, Math.abs(x90 - x10))}
                height={ROW_H - 12}
                rx={4}
                fill={color}
                fillOpacity={rec ? 0.9 : 0.32}
                stroke={rec ? "var(--accent)" : "none"}
                strokeWidth={rec ? 2 : 0}
              />
              {/* P50 marker */}
              <line x1={x50} y1={y + 2} x2={x50} y2={y + ROW_H - 2} stroke="var(--text)" strokeWidth={2} />
            </g>
          );
        })}
      </svg>

      <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]" style={{ color: "var(--text-dim)" }}>
        {rows.map((r) => {
          const rec = r.label === recommended;
          return (
            <span key={r.label} className={cn("flex items-center gap-1.5", rec && "font-semibold")} style={{ color: rec ? "var(--text)" : undefined }}>
              <span className="h-2 w-2 rounded-full" style={{ background: RISK_COLOR[r.risk_label] }} aria-hidden="true" />
              <span className="capitalize">{r.label}</span>
              <span style={{ color: RISK_COLOR[r.risk_label] }}>{r.risk_label}</span>
              <span className="tabular-nums" title="median (P50)">{money(r.p50)}</span>
              {rec && <span style={{ color: "var(--accent-text)" }}>◂ recommended</span>}
            </span>
          );
        })}
        <span className="ml-auto flex items-center gap-3">
          <span className="flex items-center gap-1"><span className="inline-block h-3 w-0.5" style={{ background: "var(--text)" }} />median</span>
          <span>bar = P10–P90 range</span>
        </span>
      </div>
    </div>
  );
}
