/**
 * Tests para os ajustes de sidebar do settings-store: clamp de largura
 * (180–480, arredondado) e posição. Complementa tests/bloco_l_settings.ts.
 */

import { describe, expect, it, beforeEach } from "vitest";
import { useSettingsStore } from "../settings-store";

beforeEach(() => {
  useSettingsStore.getState().resetSettings();
});

describe("settings-store — sidebar", () => {
  it("setSidebarWidth respeita o mínimo (180)", () => {
    useSettingsStore.getState().setSidebarWidth(50);
    expect(useSettingsStore.getState().sidebarWidth).toBe(180);
  });

  it("setSidebarWidth respeita o máximo (480)", () => {
    useSettingsStore.getState().setSidebarWidth(9999);
    expect(useSettingsStore.getState().sidebarWidth).toBe(480);
  });

  it("setSidebarWidth arredonda valores fracionários", () => {
    useSettingsStore.getState().setSidebarWidth(250.7);
    expect(useSettingsStore.getState().sidebarWidth).toBe(251);
  });

  it("setSidebarWidth mantém valores dentro da faixa", () => {
    useSettingsStore.getState().setSidebarWidth(300);
    expect(useSettingsStore.getState().sidebarWidth).toBe(300);
  });

  it("setSidebarPosition alterna entre left e right", () => {
    useSettingsStore.getState().setSidebarPosition("right");
    expect(useSettingsStore.getState().sidebarPosition).toBe("right");
    useSettingsStore.getState().setSidebarPosition("left");
    expect(useSettingsStore.getState().sidebarPosition).toBe("left");
  });
});
