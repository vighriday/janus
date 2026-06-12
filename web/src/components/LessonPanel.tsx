"use client";

import { Fragment } from "react";
import type { Precedent } from "@/lib/stream";
import { cn } from "@/lib/cn";

// The lesson text cites sources inline as [ref_id:N]. Split on those markers so
// each one renders as a citation chip the reader can click to surface the
// precedent it rests on.
const CITE = /\[ref_id:(\d+)\]/g;

// The model sometimes wraps emphasis in markdown (**bold**, *italic*); the panel
// renders plain text, so strip the markers rather than show them literally. The
// final pass removes any orphan markers left when an emphasis span straddles a
// citation marker, so a stray asterisk never reaches the screen.
function stripEmphasis(s: string): string {
  return s
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "$1")
    .replace(/\*+/g, "");
}

export function LessonPanel({
  lesson,
  precedents,
  activeRef,
  onCite,
}: {
  lesson: string;
  precedents: Precedent[];
  activeRef: number | null;
  onCite: (ref: number | null) => void;
}) {
  const byRef = new Map(precedents.map((p) => [p.ref_id, p]));
  const clean = stripEmphasis(lesson);
  const parts: Array<string | number> = [];
  let last = 0;
  for (const m of clean.matchAll(CITE)) {
    if (m.index! > last) parts.push(clean.slice(last, m.index));
    parts.push(Number(m[1]));
    last = m.index! + m[0].length;
  }
  if (last < clean.length) parts.push(clean.slice(last));

  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm leading-relaxed" style={{ color: "var(--text)" }}>
        {parts.map((part, i) =>
          typeof part === "string" ? (
            <Fragment key={i}>{part}</Fragment>
          ) : (
            <button
              key={i}
              onClick={() => onCite(activeRef === part ? null : part)}
              onMouseEnter={() => onCite(part)}
              onMouseLeave={() => onCite(null)}
              onFocus={() => onCite(part)}
              onBlur={() => onCite(null)}
              title={byRef.get(part)?.title ?? `Source ${part}`}
              aria-label={`Citation ${part}: ${byRef.get(part)?.title ?? "source"}`}
              className={cn(
                "mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded px-1 align-middle text-[11px] font-semibold tabular-nums transition",
                activeRef === part ? "ring-1" : "opacity-90",
              )}
              style={{
                background: activeRef === part ? "var(--accent)" : "var(--surface-2)",
                color: activeRef === part ? "white" : "var(--accent-text)",
              }}
            >
              {part}
            </button>
          ),
        )}
      </p>

      <ol className="flex flex-col gap-1.5">
        {precedents.map((p) => (
          <li key={p.ref_id}>
            <button
              type="button"
              onMouseEnter={() => onCite(p.ref_id)}
              onMouseLeave={() => onCite(null)}
              onFocus={() => onCite(p.ref_id)}
              onBlur={() => onCite(null)}
              onClick={() => onCite(activeRef === p.ref_id ? null : p.ref_id)}
              aria-label={`Precedent ${p.ref_id}: ${p.title}${p.score != null ? `, reranker score ${p.score.toFixed(2)}` : ""}`}
              className={cn(
                "flex w-full items-center gap-2 rounded-md border px-2.5 py-1.5 text-left text-xs transition",
                activeRef === p.ref_id && "ring-1",
              )}
              style={{
                background: "var(--surface-2)",
                borderColor: activeRef === p.ref_id ? "var(--accent)" : "var(--border)",
              }}
            >
              <span
                className="flex h-4 w-4 shrink-0 items-center justify-center rounded text-[10px] font-semibold"
                style={{ background: "var(--accent)", color: "white" }}
                aria-hidden="true"
              >
                {p.ref_id}
              </span>
              <span className="flex-1 truncate" style={{ color: "var(--text)" }}>
                {p.title}
              </span>
              {p.score != null && (
                <span className="tabular-nums" style={{ color: "var(--text-dim)" }}>
                  {p.score.toFixed(2)}
                </span>
              )}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
