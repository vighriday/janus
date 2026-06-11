"use client";

import { useMemo } from "react";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  type Node,
  type Edge,
  Handle,
  Position,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { Precedent, TraceNode } from "@/lib/stream";
import { cn } from "@/lib/cn";

// Three tiers, laid out left-to-right: the intercepted action, the precedents
// Foundry IQ retrieved, and the outcomes each precedent led to (the trace). The
// graph is the literal "we found what happened last time and followed it
// through" — retrieval plus the decision graph, made visible.

type Tier = "action" | "precedent" | "outcome";

type NodeData = {
  title: string;
  tier: Tier;
  ref?: number;
  docType?: string | null;
  active?: boolean;
};

const TIER_COLOR: Record<Tier, string> = {
  action: "var(--accent)",
  precedent: "var(--ok)",
  outcome: "var(--warn)",
};

function GraphNode({ data }: NodeProps<Node<NodeData>>) {
  return (
    <div
      className={cn(
        "rounded-md border px-2.5 py-1.5 text-[11px] leading-tight shadow-sm transition",
        data.active && "ring-2",
      )}
      style={{
        width: 150,
        background: "var(--surface-2)",
        borderColor: data.active ? "var(--accent)" : "var(--border)",
        color: "var(--text)",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div className="flex items-center gap-1.5">
        <span className="h-2 w-2 shrink-0 rounded-full" style={{ background: TIER_COLOR[data.tier] }} />
        {data.ref != null && (
          <span
            className="flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded text-[9px] font-bold"
            style={{ background: "var(--accent)", color: "white" }}
          >
            {data.ref}
          </span>
        )}
        {data.docType && (
          <span className="text-[9px] uppercase tracking-wide" style={{ color: "var(--text-dim)" }}>
            {data.docType}
          </span>
        )}
      </div>
      <div className="mt-0.5 line-clamp-2">{data.title}</div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { janus: GraphNode };

function norm(s: string | null | undefined) {
  return (s ?? "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

function buildGraph(
  precedents: Precedent[],
  traces: Record<string, TraceNode[]>,
  activeRef: number | null,
): { nodes: Node<NodeData>[]; edges: Edge[] } {
  const nodes: Node<NodeData>[] = [];
  const edges: Edge[] = [];

  nodes.push({
    id: "action",
    type: "janus",
    position: { x: 0, y: 0 },
    data: { title: "Intercepted action", tier: "action" },
  });

  // Trace entries are keyed by the decision doc_id; match each precedent to its
  // trace by title so the outcome fan-out hangs off the right precedent.
  const traceEntries = Object.entries(traces);
  const rowH = 96;
  const top = -((precedents.length - 1) * rowH) / 2;

  precedents.forEach((p, i) => {
    const pid = `p-${p.ref_id}`;
    const y = top + i * rowH;
    nodes.push({
      id: pid,
      type: "janus",
      position: { x: 230, y },
      data: { title: p.title, tier: "precedent", ref: p.ref_id, active: activeRef === p.ref_id },
    });
    edges.push({ id: `action-${pid}`, source: "action", target: pid, animated: activeRef === p.ref_id });

    const match = traceEntries.find(([, outs]) =>
      outs.some((o) => norm(o.title).includes(norm(p.title)) || norm(p.title).includes(norm(o.title))),
    );
    const outcomes = (match?.[1] ?? []).slice(0, 3);
    const oTop = y - ((outcomes.length - 1) * 56) / 2;
    outcomes.forEach((o, j) => {
      const oid = `${pid}-o-${j}`;
      nodes.push({
        id: oid,
        type: "janus",
        position: { x: 470, y: oTop + j * 56 },
        data: { title: o.title ?? "outcome", tier: "outcome", docType: o.doc_type },
      });
      edges.push({ id: `${pid}-${oid}`, source: pid, target: oid, animated: activeRef === p.ref_id });
    });
  });

  return { nodes, edges };
}

export function PrecedentGraph({
  precedents,
  traces,
  activeRef,
}: {
  precedents: Precedent[];
  traces: Record<string, TraceNode[]>;
  activeRef: number | null;
}) {
  const { nodes, edges } = useMemo(
    () => buildGraph(precedents, traces, activeRef),
    [precedents, traces, activeRef],
  );

  return (
    <div className="h-full w-full" style={{ minHeight: 220 }}>
      <ReactFlowProvider>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.15 }}
          proOptions={{ hideAttribution: true }}
          nodesDraggable={false}
          nodesConnectable={false}
          elementsSelectable={false}
          panOnDrag={false}
          zoomOnScroll={false}
          zoomOnPinch={false}
          preventScrolling={false}
        >
          <Background gap={16} color="var(--border)" />
        </ReactFlow>
      </ReactFlowProvider>
    </div>
  );
}
