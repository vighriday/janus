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
  payload: Record<string, unknown>;
}

export interface ProposedAction {
  action: string;
  summary: string;
  params?: Record<string, unknown>;
  rationale?: string;
}

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

/**
 * POST a proposed action and yield pipeline events as they stream in.
 *
 * Uses fetch + a streamed body reader rather than EventSource because the
 * request is a POST with a JSON body. The frame format is plain SSE
 * (`data: {json}\n\n`), so a future swap to AI Elements' transport is a
 * drop-in — this is the raw fallback the architecture calls for.
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
  if (!res.ok || !res.body) {
    throw new Error(`pipeline request failed: ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    // SSE events are separated by a blank line.
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
