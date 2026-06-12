// Mirrors the backend stream contract (api/janus/models/stream.py).
// The backend POSTs proposed actions to /smoke (placeholder) or the real
// pipeline endpoint and streams these events back as Server-Sent Events.

export type StepKind =
  | "guard"
  | "retrieve"
  | "trace"
  | "lesson"
  | "grounding"
  | "simulate"
  | "trust"
  | "approval"
  | "done"
  | "error";

export type StepStatus = "running" | "done" | "skipped" | "failed";

export interface StreamEvent {
  id: string;
  kind: StepKind;
  status: StepStatus;
  label: string;
  latency_ms: number | null;
  payload: StepPayload;
}

// The step-specific payloads the backend attaches (api/janus/pipeline/core.py).
// Every field is optional because a payload only carries what its step produced;
// the renderer narrows by `kind`.

export interface Precedent {
  ref_id: number;
  title: string;
  score: number | null;
}

export interface TraceNode {
  doc_id: string | null;
  doc_type: string | null;
  title: string | null;
}

export type RiskLabel = "low" | "elevated" | "high";

export interface FutureBand {
  label: string; // approve | modify | reject
  p10: number;
  p50: number;
  p90: number;
  risk_label: RiskLabel;
  mean_savings: number;
  mean_resilience_loss: number;
  drivers: {
    dependency_after: number;
    resilience_multiplier: number;
    failure_prob: number;
  };
}

export interface CausalEffect {
  dependency_high: number;
  dependency_low: number;
  resilience_loss_at_high: number;
  resilience_loss_at_low: number;
  resilience_saved: number;
}

export interface TrustComponents {
  retrieval: number;
  grounding: number;
  decisiveness: number;
}

export interface StepPayload {
  // retrieve
  subqueries?: string[];
  precedents?: Precedent[];
  // trace
  traces?: Record<string, TraceNode[]>;
  // lesson
  lesson?: string;
  // grounding
  ungrounded?: boolean;
  grounded_pct?: number;
  // simulate
  futures?: FutureBand[];
  recommended?: string;
  causal_effect?: CausalEffect;
  seed_manifest?: string;
  dependency_anchor?: number | null;
  concentration_knee?: number;
  // trust
  trust?: number;
  state?: string;
  floor?: number;
  components?: TrustComponents;
  weights?: TrustComponents;
  // approval gate (workflow path)
  run_id?: string;
  awaiting?: boolean;
}

export interface ProposedAction {
  action: string;
  summary: string;
  params?: Record<string, unknown>;
  rationale?: string;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/** Read an SSE response body and yield each `data:` frame as a StreamEvent. */
async function* readSse(res: Response): AsyncGenerator<StreamEvent> {
  if (!res.ok || !res.body) {
    throw new Error(`request failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let sep: number;
    while ((sep = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      const line = frame.split("\n").find((l) => l.startsWith("data:"));
      if (!line) continue;
      const json = line.slice(5).trim();
      if (!json) continue;
      try {
        yield JSON.parse(json) as StreamEvent;
      } catch {
        // ignore a partial / malformed frame
      }
    }
  }
}

/**
 * POST a proposed action and yield pipeline events as they stream in.
 *
 * Uses fetch + a streamed body reader rather than EventSource because the
 * request is a POST with a JSON body. On the workflow path the stream stops at
 * the approval gate (an `awaiting` frame carrying a `run_id`); resume it with
 * `resumePipeline`.
 */
export async function* runPipeline(
  action: ProposedAction,
  path = "/smoke",
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(action),
    signal,
  });
  yield* readSse(res);
}

/** Resolve a paused workflow run with the human's decision and stream the rest. */
export async function* resumePipeline(
  runId: string,
  approved: boolean,
  signal?: AbortSignal,
): AsyncGenerator<StreamEvent> {
  const res = await fetch(`${API_BASE}/resume/${runId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved }),
    signal,
  });
  yield* readSse(res);
}
