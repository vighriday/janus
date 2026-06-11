"use client";

import { useState, useRef, useCallback } from "react";
import { runPipeline, type StreamEvent, type StepStatus } from "@/lib/stream";

// The proposed action that drives the demo: an autonomous procurement agent
// wants to consolidate vendors. JANUS intercepts it.
const DEMO_ACTION = {
  action: "consolidate_vendors",
  summary:
    "Auto-approve the $250k renewal with Vendor X and consolidate two more vendors onto it.",
  params: { target_vendor: "Tessell", dependency_after: 1.0, contract_value: 250000 },
};

const statusColor: Record<StepStatus, string> = {
  running: "var(--accent)",
  done: "var(--ok)",
  skipped: "var(--text-dim)",
  failed: "var(--danger)",
};

export default function Home() {
  const [events, setEvents] = useState<Map<string, StreamEvent>>(new Map());
  const [order, setOrder] = useState<string[]>([]);
  const [running, setRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const run = useCallback(async () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setEvents(new Map());
    setOrder([]);
    setRunning(true);
    try {
      for await (const ev of runPipeline(DEMO_ACTION, "/smoke", ac.signal)) {
        setEvents((prev) => {
          const next = new Map(prev);
          next.set(ev.id, ev);
          return next;
        });
        setOrder((prev) => (prev.includes(ev.id) ? prev : [...prev, ev.id]));
      }
    } catch (err) {
      if (!ac.signal.aborted) console.error(err);
    } finally {
      setRunning(false);
    }
  }, []);

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <header className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">JANUS</h1>
        <p className="mt-1 text-sm" style={{ color: "var(--text-dim)" }}>
          A decision guardrail for autonomous enterprise agents.
        </p>
      </header>

      <section
        className="rounded-lg border p-5"
        style={{ background: "var(--surface)", borderColor: "var(--border)" }}
      >
        <div className="text-xs uppercase tracking-wide" style={{ color: "var(--text-dim)" }}>
          Proposed action — intercepted
        </div>
        <div className="mt-2 text-sm">{DEMO_ACTION.summary}</div>
        <button
          onClick={run}
          disabled={running}
          className="mt-4 rounded-md px-4 py-2 text-sm font-medium transition disabled:opacity-50"
          style={{ background: "var(--accent)", color: "white" }}
        >
          {running ? "Running…" : "Run JANUS"}
        </button>
      </section>

      <section className="mt-6 space-y-2">
        {order.map((id) => {
          const ev = events.get(id)!;
          return (
            <div
              key={id}
              className="flex items-center gap-3 rounded-md border px-4 py-3"
              style={{ background: "var(--surface-2)", borderColor: "var(--border)" }}
            >
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ background: statusColor[ev.status] }}
              />
              <span className="flex-1 text-sm">{ev.label}</span>
              <span className="text-xs" style={{ color: "var(--text-dim)" }}>
                {ev.status === "running"
                  ? "…"
                  : ev.latency_ms != null
                    ? `${ev.latency_ms}ms`
                    : ev.status}
              </span>
            </div>
          );
        })}
      </section>
    </main>
  );
}
