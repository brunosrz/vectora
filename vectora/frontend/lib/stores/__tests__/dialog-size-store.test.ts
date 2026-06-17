/**
 * Tests para o dialog-size-store: persiste o tamanho redimensionado de cada
 * diálogo por chave, com fallback nos defaults.
 */

import { describe, expect, it, beforeEach } from "vitest";
import { useDialogSizeStore } from "../dialog-size-store";

beforeEach(() => {
  useDialogSizeStore.setState({ sizes: {} });
  if (typeof localStorage !== "undefined") localStorage.clear();
});

describe("dialog-size-store", () => {
  it("getSize devolve os defaults quando a chave não foi salva", () => {
    const def = { w: 600, h: 460 };
    expect(useDialogSizeStore.getState().getSize("preferencias", def)).toBe(
      def,
    );
  });

  it("setSize persiste o tamanho e getSize o devolve", () => {
    useDialogSizeStore.getState().setSize("preferencias", { w: 800, h: 500 });
    expect(
      useDialogSizeStore.getState().getSize("preferencias", { w: 1, h: 1 }),
    ).toEqual({ w: 800, h: 500 });
  });

  it("isola tamanhos por chave de diálogo", () => {
    const s = useDialogSizeStore.getState();
    s.setSize("preferencias", { w: 800, h: 500 });
    s.setSize("administracao", { w: 900, h: 600 });
    expect(useDialogSizeStore.getState().sizes.preferencias).toEqual({
      w: 800,
      h: 500,
    });
    expect(useDialogSizeStore.getState().sizes.administracao).toEqual({
      w: 900,
      h: 600,
    });
  });
});
