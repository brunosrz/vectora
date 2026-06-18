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

  it("start com no_files cria o job em estado no_files e não pollla", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          ({
            ok: true,
            json: async () => ({
              job_id: "jnf",
              total_chunks: 0,
              status: "no_files",
            }),
          }) as Response,
      ),
    );
    const id = await useRagJobsStore.getState().start("ws1", "/vazia", "all");
    expect(id).toBe("jnf");
    const tracked = useRagJobsStore.getState().jobs.jnf;
    expect(tracked.status).toBe("no_files");
    expect(tracked.total).toBe(0);
  });

  it("start indexando registra o job; dismiss para o poll e remove", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (String(url).includes("/rag/ingest")) {
          return {
            ok: true,
            json: async () => ({
              job_id: "jix",
              total_chunks: 5,
              status: "indexing",
            }),
          } as Response;
        }
        return {
          ok: true,
          json: async () => ({
            total: 5,
            processed: 0,
            failed: 0,
            status: "indexing",
          }),
        } as Response;
      }),
    );
    const id = await useRagJobsStore.getState().start("ws1", "/docs", "code");
    expect(id).toBe("jix");
    expect(useRagJobsStore.getState().jobs.jix?.status).toBe("indexing");

    useRagJobsStore.getState().dismiss("jix");
    expect("jix" in useRagJobsStore.getState().jobs).toBe(false);
    vi.useRealTimers();
  });
});
