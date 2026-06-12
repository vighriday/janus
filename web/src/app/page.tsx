"use client";

import { useState, useRef, useCallback, useMemo } from "react";
import { runPipeline, resumePipeline, type StreamEvent, type StepKind, type StepStatus } from "@/lib/stream";
import { Panel } from "@/components/Panel";
import { ActionBar } from "@/components/ActionBar";
import { LessonPanel } from "@/components/LessonPanel";
import { PrecedentGraph } from "@/components/PrecedentGraph";
import { FuturesChart } from "@/components/FuturesChart";
import { TrustGauge } from "@/components/TrustGauge";
import { ApprovalGate } from "@/components/ApprovalGate";
import { QueryPlan } from "@/components/QueryPlan";
import { CausalContrast } from "@/components/CausalContrast";

// The intercepted scenario. A single demo case lives here; everything downstream
// is driven by the stream, and the dependency lever is the operator's to move.
const SCENARIO = {
  action: "consolidate_vendors",
  summary: "Should we consolidate the carrier-routing vendors onto one vendor?",
  targetVendor: "Tessell",
  contractValue: 3_360_000,
  description:
    "Auto-approve the carrier-routing renewal and consolidate vendors onto the top vendor.",
};

type PanelState = "idle" | "running" | "done" | "failed";

// Map a step's stream status onto a panel state. A step we haven't heard from
// yet stays idle (dimmed); once it reports, the panel lights up.
function panelState(ev: StreamEvent | undefined): PanelState {
  if (!ev) return "idle";
  if (ev.status === "running") return "running";
  if (ev.status === "failed") return "failed";
  return "done";
}

export default function Home() {
  const [dependency, setDependency] = useState(1.0);
  const [byKind, setByKind] = useState<Map<StepKind, StreamEvent>>(new Map());
  const [log, setLog] = useState<{ id: string; label: string; status: StepStatus }[]>([]);
  const [running, setRunning] = useState(false);
  const [activeRef, setActiveRef] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [runId, setRunId] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Fold a stream of events into the per-kind map and the live log.
  const ingest = useCallback((ev: StreamEvent) => {
    setByKind((prev) => new Map(prev).set(ev.kind, ev));
    if (ev.payload.run_id) setRunId(ev.payload.run_id);
    setLog((prev) => {
      const i = prev.findIndex((e) => e.id === ev.id);
      const row = { id: ev.id, label: ev.label, status: ev.status };
      if (i === -1) return [...prev, row];
      const next = [...prev];
      next[i] = row;
      return next;
    });
  }, []);

  const run = useCallback(async () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    setByKind(new Map());
    setLog([]);
    setActiveRef(null);
    setError(null);
    setRunId(null);
    setRunning(true);
    const action = {
      action: SCENARIO.action,
      summary: SCENARIO.summary,
      params: {
        target_vendor: SCENARIO.targetVendor,
        dependency_after: dependency,
        contract_value: SCENARIO.contractValue,
      },
    };
    try {
      // The workflow path runs the Microsoft Agent Framework spine and stops at
      // the human gate; the run is held server-side until the operator decides.
      for await (const ev of runPipeline(action, "/invoke-workflow", ac.signal)) {
        ingest(ev);
      }
    } catch (err) {
      if (!ac.signal.aborted) {
        console.error(err);
        setError(
          "The pipeline could not complete — the backend may be unreachable or an Azure call failed. Check that the API is running, then run again.",
        );
      }
    } finally {
      setRunning(false);
    }
  }, [dependency, ingest]);

  // The human's decision at the gate: resume the paused workflow over the wire.
  const decide = useCallback(
    async (approved: boolean) => {
      if (!runId) return;
      const ac = new AbortController();
      try {
        for await (const ev of resumePipeline(runId, approved, ac.signal)) {
          ingest(ev);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setRunId(null);
      }
    },
    [runId, ingest],
  );

  const retrieve = byKind.get("retrieve");
  const trace = byKind.get("trace");
  const lesson = byKind.get("lesson");
  const grounding = byKind.get("grounding");
  const simulate = byKind.get("simulate");
  const trust = byKind.get("trust");
  const approval = byKind.get("approval");

  const precedents = retrieve?.payload.precedents ?? [];
  const subqueries = retrieve?.payload.subqueries ?? [];
  const traces = trace?.payload.traces ?? {};
  const lessonText = lesson?.payload.lesson ?? "";
  const futures = simulate?.payload.futures ?? [];
  const causal = simulate?.payload.causal_effect;
  const recommended = simulate?.payload.recommended ?? approval?.payload.recommended ?? "";
  const trustVal = trust?.payload.trust;
  const components = trust?.payload.components;
  const weights = trust?.payload.weights;

  const groundedBadge = useMemo(() => {
    const pct = grounding?.payload.grounded_pct;
    if (pct == null) return null;
    return (
      <span style={{ color: grounding?.payload.ungrounded ? "var(--warn)" : "var(--ok)" }}>
        {pct}% grounded{grounding?.payload.ungrounded ? " · flagged" : ""}
      </span>
    );
  }, [grounding]);

  return (
    <main className="mx-auto max-w-6xl px-5 py-8">
      <header className="mb-5 flex items-baseline justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">JANUS</h1>
          <p className="text-xs" style={{ color: "var(--text-dim)" }}>
            A decision guardrail for autonomous enterprise agents — it intercepts, reasons, and pauses for a human.
          </p>
        </div>
        {recommended && !running && (
          <div className="text-xs" style={{ color: "var(--text-dim)" }}>
            verdict:{" "}
            <span className="font-semibold uppercase" style={{ color: "var(--text)" }}>
              {recommended}
            </span>
          </div>
        )}
      </header>

      <ActionBar
        dependency={dependency}
        onDependency={setDependency}
        running={running}
        onRun={run}
        contractValue={SCENARIO.contractValue}
        description={SCENARIO.description}
        knee={simulate?.payload.concentration_knee ?? 0.7}
      />

      {error && (
        <div
          role="alert"
          className="mt-4 rounded-lg border px-4 py-3 text-sm"
          style={{ borderColor: "var(--danger)", background: "var(--surface)", color: "var(--text)" }}
        >
          {error}
        </div>
      )}

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
        {/* Lesson — spans two columns, the grounded reasoning */}
        <Panel
          title="Grounded lesson"
          state={panelState(lesson)}
          badge={groundedBadge}
          className="lg:col-span-2"
        >
          {lessonText ? (
            <LessonPanel
              lesson={lessonText}
              precedents={precedents}
              activeRef={activeRef}
              onCite={setActiveRef}
            />
          ) : (
            <Empty label="The cited principle JANUS extracts from precedent appears here." />
          )}
        </Panel>

        {/* Trust */}
        <Panel title="Trust" state={panelState(trust)}>
          {trustVal != null && components ? (
            <TrustGauge
              trust={trustVal}
              components={components}
              weights={weights}
              floor={trust?.payload.floor}
              state={trust?.payload.state}
              capped={grounding?.payload.ungrounded}
            />
          ) : (
            <Empty label="Composed from retrieval, grounding, and decisiveness." />
          )}
        </Panel>

        {/* Query plan — the agentic retrieval beat */}
        <Panel title="Query plan — Foundry IQ" state={panelState(retrieve)}>
          {subqueries.length ? (
            <QueryPlan subqueries={subqueries} />
          ) : (
            <Empty label="The subqueries Foundry IQ planned to answer the decision question." />
          )}
        </Panel>

        {/* Precedent graph — spans two columns */}
        <Panel title="Precedent graph" state={panelState(trace)} className="lg:col-span-2 min-h-[260px]">
          {precedents.length ? (
            <PrecedentGraph precedents={precedents} traces={traces} activeRef={activeRef} />
          ) : (
            <Empty label="Retrieved precedents and the outcomes they led to, traced in the decision graph." />
          )}
        </Panel>

        {/* Approval gate */}
        <Panel title="Human approval" state={panelState(approval)}>
          {recommended ? (
            <ApprovalGate
              recommended={recommended}
              lesson={lessonText}
              futures={futures}
              awaiting={runId != null}
              onDecide={decide}
            />
          ) : (
            <Empty label="JANUS recommends; a human approves or overrides." />
          )}
        </Panel>

        {/* Futures — spans two columns */}
        <Panel
          title="Three futures — simulated, not authored"
          state={panelState(simulate)}
          badge={
            simulate?.payload.seed_manifest ? (
              <span className="tabular-nums" style={{ color: "var(--text-dim)" }} title="run seed manifest (SHA-256)">
                seed {simulate.payload.seed_manifest.slice(0, 8)}
              </span>
            ) : null
          }
          className="lg:col-span-2 min-h-[220px]"
        >
          {futures.length ? (
            <FuturesChart futures={futures} recommended={recommended} />
          ) : (
            <Empty label="A seeded Monte Carlo over a transparent cost model — P10/P50/P90 per future. The guardrail refuses the catastrophic tail." />
          )}
        </Panel>

        {/* Causal contrast — the DoWhy do() result */}
        <Panel title="Causal contrast — do()" state={panelState(simulate)}>
          {causal ? (
            <CausalContrast causal={causal} />
          ) : (
            <Empty label="A do()-intervention: what moving the dependency lever does to expected resilience loss, all else fixed." />
          )}
        </Panel>
      </div>

      {/* Live step log */}
      <div className="mt-4 rounded-lg border px-4 py-3" style={{ background: "var(--surface)", borderColor: "var(--border)" }}>
        <div className="text-[11px] uppercase tracking-wider" style={{ color: "var(--text-dim)" }}>
          Pipeline
        </div>
        <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {log.length === 0 && <span style={{ color: "var(--text-dim)" }}>Idle — run JANUS to intercept the action.</span>}
          {log.map((e) => {
            const glyph =
              e.status === "done" ? "✓" : e.status === "failed" ? "✕" : e.status === "running" ? "▸" : "·";
            const tone =
              e.status === "done"
                ? "var(--ok)"
                : e.status === "failed"
                  ? "var(--danger)"
                  : e.status === "running"
                    ? "var(--accent-text)"
                    : "var(--text-dim)";
            return (
              <span key={e.id} className="flex items-center gap-1.5">
                <span className="tabular-nums" style={{ color: tone }} aria-hidden="true">
                  {glyph}
                </span>
                <span style={{ color: e.status === "running" ? "var(--text)" : "var(--text-dim)" }}>{e.label}</span>
              </span>
            );
          })}
        </div>
      </div>
    </main>
  );
}

function Empty({ label }: { label: string }) {
  return (
    <div className="flex flex-1 items-center text-xs" style={{ color: "var(--text-dim)" }}>
      {label}
    </div>
  );
}
