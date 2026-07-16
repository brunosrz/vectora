import { describe, it, expect, beforeEach } from "vitest";
import {
  signalWorkspacePreChosen,
  consumeWorkspacePreChosen,
  signalCreateNewWorkspacePreNav,
  consumeCreateNewWorkspacePreNav,
} from "../new-session-signal";

beforeEach(() => {
  consumeWorkspacePreChosen();
  consumeCreateNewWorkspacePreNav();
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

describe("new-session-signal — 'criar novo workspace' (sinal independente)", () => {
  it("signal → consume retorna true; segundo consume retorna false (one-shot)", () => {
    signalCreateNewWorkspacePreNav();
    expect(consumeCreateNewWorkspacePreNav()).toBe(true);
    expect(consumeCreateNewWorkspacePreNav()).toBe(false);
  });

  it("não interfere no sinal de workspace pré-escolhido (independentes)", () => {
    signalWorkspacePreChosen();
    signalCreateNewWorkspacePreNav();
    expect(consumeCreateNewWorkspacePreNav()).toBe(true);
    // o outro sinal continua pendente — consumo de um não afeta o outro
    expect(consumeWorkspacePreChosen()).toBe(true);
  });
});
