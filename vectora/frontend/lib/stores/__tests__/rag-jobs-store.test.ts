/**
 * Tests para o `rag-jobs-store`: parte determinística (dismiss, falha de
 * start). O poll por setInterval não é exercido aqui.
 */

import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import { useRagJobsStore, type RagJob } from "../rag-jobs-store";

beforeEach(() => {
  useRagJobsStore.setState({ jobs: {} });
});

afterEach(() => {
  vi.restoreAllMocks();
});

function job(jobId: string, over: Partial<RagJob> = {}): RagJob {
  return {
    jobId,
    workspaceId: "ws1",
    path: "/x",
    total: 10,
    processed: 0,
    failed: 0,
    status: "indexing",
    ...over,
  };
}

describe("rag-jobs-store", () => {
  it("dismiss remove o job da lista", () => {
    useRagJobsStore.setState({ jobs: { j1: job("j1") } });
    useRagJobsStore.getState().dismiss("j1");
    expect("j1" in useRagJobsStore.getState().jobs).toBe(false);
  });

  it("dismiss de job inexistente não quebra", () => {
    expect(() => useRagJobsStore.getState().dismiss("nope")).not.toThrow();
  });

  it("guarda o motivo quando o job está pausado (rate limit)", () => {
    useRagJobsStore.setState({
      jobs: {
        j1: job("j1", { status: "paused", errorReason: "Cohere 429" }),
      },
    });
    expect(useRagJobsStore.getState().jobs.j1.status).toBe("paused");
    expect(useRagJobsStore.getState().jobs.j1.errorReason).toBe("Cohere 429");
  });

  it("start devolve null quando o POST falha", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false }) as Response),
    );
    const result = await useRagJobsStore
      .getState()
      .start("ws1", "/pasta", "all");
    expect(result).toBeNull();
    expect(Object.keys(useRagJobsStore.getState().jobs)).toHaveLength(0);
  });
});
