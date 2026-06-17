/**
 * Tests para o new-thread-registry: marca/limpa threads recém-criadas e
 * expira por TTL (5 min).
 */

import { describe, expect, it, afterEach, vi } from "vitest";
import { markAsNew, isNew, clearNew } from "../new-thread-registry";

afterEach(() => {
  vi.useRealTimers();
  clearNew("t1");
  clearNew("t2");
});

describe("new-thread-registry", () => {
  it("isNew é false para thread nunca marcada", () => {
    expect(isNew("desconhecida")).toBe(false);
  });

  it("markAsNew torna a thread 'nova' e clearNew remove", () => {
    markAsNew("t1");
    expect(isNew("t1")).toBe(true);
    clearNew("t1");
    expect(isNew("t1")).toBe(false);
  });

  it("expira a marcação após o TTL de 5 min", () => {
    vi.useFakeTimers();
    markAsNew("t2");
    expect(isNew("t2")).toBe(true);
    vi.advanceTimersByTime(5 * 60 * 1000 + 1);
    expect(isNew("t2")).toBe(false);
  });
});
