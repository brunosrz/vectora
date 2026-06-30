import { describe, it, expect, beforeEach } from "vitest";
import {
  signalWorkspacePreChosen,
  consumeWorkspacePreChosen,
} from "../new-session-signal";

beforeEach(() => {
  consumeWorkspacePreChosen();
});

describe("new-session-signal", () => {
  it("começa sem sinal pendente", () => {
    expect(consumeWorkspacePreChosen()).toBe(false);
  });

  it("signal → consume retorna true", () => {
    signalWorkspacePreChosen();
    expect(consumeWorkspacePreChosen()).toBe(true);
  });

  it("consume é one-shot: segundo consume retorna false", () => {
    signalWorkspacePreChosen();
    consumeWorkspacePreChosen();
    expect(consumeWorkspacePreChosen()).toBe(false);
  });

  it("dois signals consecutivos continuam sendo consumidos uma vez", () => {
    signalWorkspacePreChosen();
    signalWorkspacePreChosen();
    expect(consumeWorkspacePreChosen()).toBe(true);
    expect(consumeWorkspacePreChosen()).toBe(false);
  });

  it("múltiplos cycles funcionam independentemente", () => {
    for (let i = 0; i < 3; i++) {
      expect(consumeWorkspacePreChosen()).toBe(false);
      signalWorkspacePreChosen();
      expect(consumeWorkspacePreChosen()).toBe(true);
      expect(consumeWorkspacePreChosen()).toBe(false);
    }
  });

  it("consume sem signal prévio é idempotente", () => {
    consumeWorkspacePreChosen();
    consumeWorkspacePreChosen();
    expect(consumeWorkspacePreChosen()).toBe(false);
  });
});
