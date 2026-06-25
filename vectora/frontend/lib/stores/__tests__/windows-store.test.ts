/**
 * Tests para o windows-store: janelas flutuantes com abas por workspace
 * (open/closeTab/setActiveTab/close/focus/minimize/restore/setBounds).
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useWindowsStore } from "../windows-store";

const BASE_Z = 100;
const s = () => useWindowsStore.getState();
const winOf = (id: string) => s().windows.find((w) => w.id === id);

beforeEach(() => {
  useWindowsStore.setState({ windows: [], topZ: BASE_Z });
  if (typeof localStorage !== "undefined") localStorage.clear();
});

describe("windows-store — open", () => {
  it("começa sem janelas", () => {
    expect(s().windows).toHaveLength(0);
  });

  it("open cria uma janela com id = workspaceId", () => {
    s().open("ws1", "src/a.ts");
    expect(winOf("ws1")).toBeDefined();
  });

  it("open define activeTab e title a partir do basename do path", () => {
    s().open("ws1", "src/deep/file.ts");
    const w = winOf("ws1")!;
    expect(w.activeTab).toBe("src/deep/file.ts");
    expect(w.title).toBe("file.ts");
  });

  it("open usa dimensões padrão 640x460", () => {
    s().open("ws1", "a.ts");
    const w = winOf("ws1")!;
    expect(w.w).toBe(640);
    expect(w.h).toBe(460);
  });

  it("open atribui zIndex acima do topo e incrementa topZ", () => {
    s().open("ws1", "a.ts");
    expect(s().topZ).toBe(BASE_Z + 1);
    expect(winOf("ws1")?.zIndex).toBe(BASE_Z + 1);
  });

  it("abrir segundo arquivo no mesmo workspace adiciona aba (não nova janela)", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    expect(s().windows).toHaveLength(1);
    expect(winOf("ws1")?.tabs).toEqual(["a.ts", "b.ts"]);
  });

  it("abrir segundo arquivo ativa-o como activeTab", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    expect(winOf("ws1")?.activeTab).toBe("b.ts");
    expect(winOf("ws1")?.title).toBe("b.ts");
  });

  it("open do mesmo path não duplica a aba — ativa e traz pro topo", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    s().open("ws1", "a.ts");
    expect(winOf("ws1")?.tabs).toEqual(["a.ts", "b.ts"]);
    expect(winOf("ws1")?.activeTab).toBe("a.ts");
  });

  it("open de workspace diferente cria janela separada", () => {
    s().open("ws1", "a.ts");
    s().open("ws2", "a.ts");
    expect(s().windows).toHaveLength(2);
    expect(winOf("ws1")).toBeDefined();
    expect(winOf("ws2")).toBeDefined();
  });

  it("open restaura janela minimizada ao abrir aba existente", () => {
    s().open("ws1", "a.ts");
    s().minimize("ws1");
    s().open("ws1", "a.ts");
    expect(winOf("ws1")?.minimized).toBe(false);
  });

  it("janelas novas cascateiam x/y", () => {
    s().open("ws1", "a.ts");
    s().open("ws2", "b.ts");
    expect(winOf("ws1")?.x).not.toBe(winOf("ws2")?.x);
  });

  it("path sem barra usa o próprio path como título", () => {
    s().open("ws1", "README");
    expect(winOf("ws1")?.title).toBe("README");
  });
});

describe("windows-store — close", () => {
  it("close remove a janela inteira", () => {
    s().open("ws1", "a.ts");
    s().close("ws1");
    expect(winOf("ws1")).toBeUndefined();
  });

  it("close de janela inexistente é no-op", () => {
    s().open("ws1", "a.ts");
    s().close("ghost");
    expect(s().windows).toHaveLength(1);
  });

  it("close não afeta outras janelas", () => {
    s().open("ws1", "a.ts");
    s().open("ws2", "a.ts");
    s().close("ws1");
    expect(winOf("ws2")).toBeDefined();
  });
});

describe("windows-store — closeTab", () => {
  it("closeTab remove a aba", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    s().closeTab("ws1", "a.ts");
    expect(winOf("ws1")?.tabs).toEqual(["b.ts"]);
  });

  it("closeTab da última aba fecha a janela", () => {
    s().open("ws1", "a.ts");
    s().closeTab("ws1", "a.ts");
    expect(winOf("ws1")).toBeUndefined();
  });

  it("closeTab na aba ativa ativa a aba anterior", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    s().open("ws1", "c.ts");
    s().closeTab("ws1", "c.ts");
    expect(winOf("ws1")?.activeTab).toBe("b.ts");
  });

  it("closeTab na primeira aba ativa a próxima", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    s().setActiveTab("ws1", "a.ts");
    s().closeTab("ws1", "a.ts");
    expect(winOf("ws1")?.activeTab).toBe("b.ts");
  });

  it("closeTab em aba não-ativa não muda a aba ativa", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    s().closeTab("ws1", "a.ts");
    expect(winOf("ws1")?.activeTab).toBe("b.ts");
  });

  it("closeTab de janela inexistente é no-op", () => {
    s().open("ws1", "a.ts");
    expect(() => s().closeTab("ghost", "a.ts")).not.toThrow();
    expect(s().windows).toHaveLength(1);
  });
});

describe("windows-store — setActiveTab", () => {
  it("setActiveTab troca a aba ativa", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    s().setActiveTab("ws1", "a.ts");
    expect(winOf("ws1")?.activeTab).toBe("a.ts");
    expect(winOf("ws1")?.title).toBe("a.ts");
  });

  it("setActiveTab com path não existente na janela é no-op", () => {
    s().open("ws1", "a.ts");
    s().setActiveTab("ws1", "nonexistent.ts");
    expect(winOf("ws1")?.activeTab).toBe("a.ts");
  });
});

describe("windows-store — focus / z-order", () => {
  it("focus traz a janela para o topo", () => {
    s().open("ws1", "a.ts");
    s().open("ws2", "b.ts");
    s().focus("ws1");
    expect(winOf("ws1")?.zIndex).toBe(s().topZ);
  });

  it("focus na janela já no topo é no-op", () => {
    s().open("ws1", "a.ts");
    const topZBefore = s().topZ;
    s().focus("ws1");
    expect(s().topZ).toBe(topZBefore);
  });

  it("focus em janela inexistente é no-op", () => {
    s().open("ws1", "a.ts");
    const before = s().topZ;
    s().focus("ghost");
    expect(s().topZ).toBe(before);
  });

  it("topZ cresce monotonicamente ao focar", () => {
    s().open("ws1", "a.ts");
    s().open("ws2", "b.ts");
    const z1 = s().topZ;
    s().focus("ws1");
    expect(s().topZ).toBeGreaterThan(z1);
  });
});

describe("windows-store — minimize / restore", () => {
  it("minimize marca minimized=true", () => {
    s().open("ws1", "a.ts");
    s().minimize("ws1");
    expect(winOf("ws1")?.minimized).toBe(true);
  });

  it("minimize de inexistente não quebra", () => {
    s().open("ws1", "a.ts");
    expect(() => s().minimize("ghost")).not.toThrow();
    expect(s().windows).toHaveLength(1);
  });

  it("restore marca minimized=false e traz pro topo", () => {
    s().open("ws1", "a.ts");
    s().minimize("ws1");
    s().restore("ws1");
    const w = winOf("ws1")!;
    expect(w.minimized).toBe(false);
    expect(w.zIndex).toBe(s().topZ);
  });

  it("restore incrementa topZ", () => {
    s().open("ws1", "a.ts");
    const before = s().topZ;
    s().restore("ws1");
    expect(s().topZ).toBe(before + 1);
  });
});

describe("windows-store — setBounds", () => {
  it("setBounds atualiza posição e tamanho", () => {
    s().open("ws1", "a.ts");
    s().setBounds("ws1", { x: 10, y: 20, w: 300, h: 200 });
    expect(winOf("ws1")).toMatchObject({ x: 10, y: 20, w: 300, h: 200 });
  });

  it("setBounds parcial atualiza só os campos dados", () => {
    s().open("ws1", "a.ts");
    s().setBounds("ws1", { x: 5 });
    const w = winOf("ws1")!;
    expect(w.x).toBe(5);
    expect(w.w).toBe(640);
  });

  it("setBounds de janela inexistente é no-op", () => {
    s().open("ws1", "a.ts");
    s().setBounds("ghost", { x: 999 });
    expect(winOf("ws1")?.x).not.toBe(999);
  });
});
