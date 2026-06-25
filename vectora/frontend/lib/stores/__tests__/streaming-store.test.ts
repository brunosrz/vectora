/**
 * Tests para o streaming-store: qual thread está com stream SSE ativo.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useStreamingStore } from "../streaming-store";

beforeEach(() => {
  useStreamingStore.setState({ streamingThreadId: null });
});

describe("streaming-store", () => {
  it("streamingThreadId começa null", () => {
    expect(useStreamingStore.getState().streamingThreadId).toBeNull();
  });

  it("setStreaming define o thread ativo", () => {
    useStreamingStore.getState().setStreaming("t1");
    expect(useStreamingStore.getState().streamingThreadId).toBe("t1");
  });

  it("setStreaming(null) limpa o thread ativo", () => {
    const s = useStreamingStore.getState();
    s.setStreaming("t1");
    s.setStreaming(null);
    expect(useStreamingStore.getState().streamingThreadId).toBeNull();
  });

  it("setStreaming sobrescreve o thread anterior", () => {
    const s = useStreamingStore.getState();
    s.setStreaming("t1");
    s.setStreaming("t2");
    expect(useStreamingStore.getState().streamingThreadId).toBe("t2");
  });

  it("setStreaming com o mesmo id mantém o valor", () => {
    const s = useStreamingStore.getState();
    s.setStreaming("t1");
    s.setStreaming("t1");
    expect(useStreamingStore.getState().streamingThreadId).toBe("t1");
  });

  it("aceita string vazia", () => {
    useStreamingStore.getState().setStreaming("");
    expect(useStreamingStore.getState().streamingThreadId).toBe("");
  });

  it("alterna entre threads", () => {
    const s = useStreamingStore.getState();
    s.setStreaming("a");
    expect(useStreamingStore.getState().streamingThreadId).toBe("a");
    s.setStreaming("b");
    expect(useStreamingStore.getState().streamingThreadId).toBe("b");
    s.setStreaming(null);
    expect(useStreamingStore.getState().streamingThreadId).toBeNull();
  });

  it("null após null é no-op", () => {
    useStreamingStore.getState().setStreaming(null);
    expect(useStreamingStore.getState().streamingThreadId).toBeNull();
  });

  it("ids longos (uuid) são preservados", () => {
    const uuid = "550e8400-e29b-41d4-a716-446655440000";
    useStreamingStore.getState().setStreaming(uuid);
    expect(useStreamingStore.getState().streamingThreadId).toBe(uuid);
  });
});
