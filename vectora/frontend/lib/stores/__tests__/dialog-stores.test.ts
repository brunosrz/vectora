/**
 * Tests para os stores de diálogo de configurações (open/openAt/setTab).
 * São simples mas controlam deep-link sem prop drilling — vale cobrir.
 */

import { describe, expect, it, beforeEach } from "vitest";
import { useEnvironmentDialogStore } from "../environment-dialog-store";
import { usePreferenciasDialogStore } from "../preferencias-dialog-store";
import { useAdministracaoDialogStore } from "../administracao-dialog-store";

describe("environment-dialog-store", () => {
  beforeEach(() =>
    useEnvironmentDialogStore.setState({ open: false, tab: "envs" }),
  );

  it("openAt abre no tab pedido", () => {
    useEnvironmentDialogStore.getState().openAt("plugins");
    expect(useEnvironmentDialogStore.getState().open).toBe(true);
    expect(useEnvironmentDialogStore.getState().tab).toBe("plugins");
  });

  it("openAt sem argumento cai no default 'envs'", () => {
    useEnvironmentDialogStore.getState().openAt();
    expect(useEnvironmentDialogStore.getState().tab).toBe("envs");
  });

  it("setOpen e setTab atualizam o estado", () => {
    useEnvironmentDialogStore.getState().setTab("integracoes");
    useEnvironmentDialogStore.getState().setOpen(true);
    expect(useEnvironmentDialogStore.getState().tab).toBe("integracoes");
    expect(useEnvironmentDialogStore.getState().open).toBe(true);
  });
});

describe("preferencias-dialog-store", () => {
  beforeEach(() =>
    usePreferenciasDialogStore.setState({ open: false, tab: "preferencias" }),
  );

  it("openAt abre no tab pedido", () => {
    usePreferenciasDialogStore.getState().openAt("memoria");
    expect(usePreferenciasDialogStore.getState().open).toBe(true);
    expect(usePreferenciasDialogStore.getState().tab).toBe("memoria");
  });

  it("openAt sem argumento cai no default 'preferencias'", () => {
    usePreferenciasDialogStore.getState().openAt();
    expect(usePreferenciasDialogStore.getState().tab).toBe("preferencias");
  });
});

describe("administracao-dialog-store", () => {
  beforeEach(() =>
    useAdministracaoDialogStore.setState({ open: false, subTab: undefined }),
  );

  it("openAt abre na sub-aba pedida", () => {
    useAdministracaoDialogStore.getState().openAt("storage");
    expect(useAdministracaoDialogStore.getState().open).toBe(true);
    expect(useAdministracaoDialogStore.getState().subTab).toBe("storage");
  });

  it("setSubTab pode limpar a sub-aba (undefined)", () => {
    useAdministracaoDialogStore.getState().setSubTab("users");
    useAdministracaoDialogStore.getState().setSubTab(undefined);
    expect(useAdministracaoDialogStore.getState().subTab).toBeUndefined();
  });
});
