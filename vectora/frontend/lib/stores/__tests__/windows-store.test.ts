/**
 * Tests para o windows-store: janelas flutuantes (open/close/focus/minimize/
 * restore/setBounds) e z-order.
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

  it("open cria uma janela com id workspaceId::path", () => {
    s().open("ws1", "src/a.ts");
    expect(winOf("ws1::src/a.ts")).toBeDefined();
  });

  it("open define o título a partir do basename", () => {
    s().open("ws1", "src/deep/file.ts");
    expect(winOf("ws1::src/deep/file.ts")?.title).toBe("file.ts");
  });

  it("open usa dimensões padrão 640x460", () => {
    s().open("ws1", "a.ts");
    const w = winOf("ws1::a.ts")!;
    expect(w.w).toBe(640);
    expect(w.h).toBe(460);
  });

  it("open atribui zIndex acima do topo e incrementa topZ", () => {
    s().open("ws1", "a.ts");
    expect(s().topZ).toBe(BASE_Z + 1);
    expect(winOf("ws1::a.ts")?.zIndex).toBe(BASE_Z + 1);
  });

  it("open de paths distintos cria janelas distintas", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    expect(s().windows).toHaveLength(2);
  });

  it("open do mesmo path não duplica — restaura e traz pro topo", () => {
    s().open("ws1", "a.ts");
    s().minimize("ws1::a.ts");
    s().open("ws1", "a.ts");
    expect(s().windows).toHaveLength(1);
    const w = winOf("ws1::a.ts")!;
    expect(w.minimized).toBe(false);
    expect(w.zIndex).toBe(s().topZ);
  });

  it("janelas novas cascateiam x/y", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    expect(winOf("ws1::a.ts")?.x).not.toBe(winOf("ws1::b.ts")?.x);
  });

  it("path sem barra usa o próprio path como título", () => {
    s().open("ws1", "README");
    expect(winOf("ws1::README")?.title).toBe("README");
  });
});

describe("windows-store — close", () => {
  it("close remove a janela", () => {
    s().open("ws1", "a.ts");
    s().close("ws1::a.ts");
    expect(winOf("ws1::a.ts")).toBeUndefined();
  });

  it("close de janela inexistente é no-op", () => {
    s().open("ws1", "a.ts");
    s().close("ghost");
    expect(s().windows).toHaveLength(1);
  });

  it("close não afeta as outras janelas", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    s().close("ws1::a.ts");
    expect(winOf("ws1::b.ts")).toBeDefined();
  });
});

describe("windows-store — focus / z-order", () => {
  it("focus traz a janela para o topo", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts"); // b no topo
    s().focus("ws1::a.ts");
    expect(winOf("ws1::a.ts")?.zIndex).toBe(s().topZ);
  });

  it("focus na janela já no topo é no-op", () => {
    s().open("ws1", "a.ts");
    const topZBefore = s().topZ;
    s().focus("ws1::a.ts");
    expect(s().topZ).toBe(topZBefore);
  });

  it("focus em janela inexistente é no-op", () => {
    s().open("ws1", "a.ts");
    const before = s().topZ;
    s().focus("ghost");
    expect(s().topZ).toBe(before);
  });

  it("focar A depois B coloca B no topo", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    s().focus("ws1::a.ts");
    s().focus("ws1::b.ts");
    expect(winOf("ws1::b.ts")!.zIndex).toBeGreaterThan(
      winOf("ws1::a.ts")!.zIndex,
    );
  });

  it("topZ cresce monotonicamente ao focar", () => {
    s().open("ws1", "a.ts");
    s().open("ws1", "b.ts");
    const z1 = s().topZ;
    s().focus("ws1::a.ts");
    expect(s().topZ).toBeGreaterThan(z1);
  });
});

describe("windows-store — minimize / restore", () => {
  it("minimize marca minimized=true", () => {
    s().open("ws1", "a.ts");
    s().minimize("ws1::a.ts");
    expect(winOf("ws1::a.ts")?.minimized).toBe(true);
  });

  it("minimize de inexistente não quebra", () => {
    s().open("ws1", "a.ts");
    expect(() => s().minimize("ghost")).not.toThrow();
    expect(s().windows).toHaveLength(1);
  });

  it("restore marca minimized=false e traz pro topo", () => {
    s().open("ws1", "a.ts");
    s().minimize("ws1::a.ts");
    s().restore("ws1::a.ts");
    const w = winOf("ws1::a.ts")!;
    expect(w.minimized).toBe(false);
    expect(w.zIndex).toBe(s().topZ);
  });

  it("restore incrementa topZ", () => {
    s().open("ws1", "a.ts");
    const before = s().topZ;
    s().restore("ws1::a.ts");
    expect(s().topZ).toBe(before + 1);
  });
});

describe("windows-store — setBounds", () => {
  it("setBounds atualiza posição e tamanho", () => {
    s().open("ws1", "a.ts");
    s().setBounds("ws1::a.ts", { x: 10, y: 20, w: 300, h: 200 });
    expect(winOf("ws1::a.ts")).toMatchObject({ x: 10, y: 20, w: 300, h: 200 });
  });

  it("setBounds parcial atualiza só os campos dados", () => {
    s().open("ws1", "a.ts");
    s().setBounds("ws1::a.ts", { x: 5 });
    const w = winOf("ws1::a.ts")!;
    expect(w.x).toBe(5);
    expect(w.w).toBe(640); // inalterado
  });

  it("setBounds de janela inexistente é no-op", () => {
    s().open("ws1", "a.ts");
    s().setBounds("ghost", { x: 999 });
    expect(winOf("ws1::a.ts")?.x).not.toBe(999);
  });
});
