// @vitest-environment node
/**
 * workspace-choice-registry — lembra se o usuário já escolheu o workspace de uma
 * thread, para a rota de sessão não reabrir o seletor (evita loop no confirm).
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  markWorkspaceChosen,
  isWorkspaceChosen,
} from "../workspace-choice-registry";

afterEach(() => {
  vi.useRealTimers();
});

describe("workspace-choice-registry", () => {
  it("thread desconhecida não foi escolhida", () => {
    expect(isWorkspaceChosen("nunca-visto")).toBe(false);
  });

  it("marca e reconhece a escolha", () => {
    markWorkspaceChosen("t1");
    expect(isWorkspaceChosen("t1")).toBe(true);
  });

  it("a marcação expira após o TTL (5min)", () => {
    vi.useFakeTimers();
    markWorkspaceChosen("t2");
    expect(isWorkspaceChosen("t2")).toBe(true);
    vi.advanceTimersByTime(5 * 60 * 1000 + 1);
    expect(isWorkspaceChosen("t2")).toBe(false);
  });

  it("ids distintos não se misturam", () => {
    markWorkspaceChosen("a");
    expect(isWorkspaceChosen("a")).toBe(true);
    expect(isWorkspaceChosen("b")).toBe(false);
  });
});
