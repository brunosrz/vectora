/**
 * TDD — windows-store (workstation flutuante)
 *
 * Cobre open/close/focus/minimize/restore/setBounds e o z-order incremental.
 * O store é singleton por módulo — reseta via setState entre casos.
 */

import { describe, it, expect, beforeEach } from "vitest";
import { useWindowsStore } from "../lib/stores/windows-store";

const WS = "ws-1";
const PATH_A = "src/main.ts";
const PATH_B = "README.md";

function reset() {
  useWindowsStore.setState({ windows: [], topZ: 100 });
}

function open(wsId = WS, path = PATH_A) {
  useWindowsStore.getState().open(wsId, path);
}

function idOf(wsId = WS, path = PATH_A) {
  return `${wsId}::${path}`;
}

describe("windows-store", () => {
  beforeEach(reset);

  // ── open ────────────────────────────────────────────────────────────────────

  it("open — cria janela com campos corretos", () => {
    open();
    const { windows, topZ } = useWindowsStore.getState();
    expect(windows).toHaveLength(1);
    const win = windows[0];
    expect(win.id).toBe(idOf());
    expect(win.workspaceId).toBe(WS);
    expect(win.path).toBe(PATH_A);
    expect(win.title).toBe("main.ts");
    expect(win.minimized).toBe(false);
    expect(win.w).toBe(640);
    expect(win.h).toBe(460);
    expect(win.zIndex).toBe(topZ);
  });

  it("open — incrementa topZ a cada janela nova", () => {
    open(WS, PATH_A);
    const z1 = useWindowsStore.getState().topZ;
    open(WS, PATH_B);
    const z2 = useWindowsStore.getState().topZ;
    expect(z2).toBeGreaterThan(z1);
  });

  it("open — cascata: posição diferente para janelas sucessivas", () => {
    open(WS, PATH_A);
    open(WS, PATH_B);
    const [a, b] = useWindowsStore.getState().windows;
    expect(b.x).toBeGreaterThan(a.x);
    expect(b.y).toBeGreaterThan(a.y);
  });

  it("open — reabre janela existente: restaura e foca (não duplica)", () => {
    open();
    useWindowsStore.getState().minimize(idOf());
    open(); // re-abre a mesma
    const { windows } = useWindowsStore.getState();
    expect(windows).toHaveLength(1);
    expect(windows[0].minimized).toBe(false);
  });

  it("open — title usa basename do path", () => {
    useWindowsStore.getState().open(WS, "deep/nested/file.tsx");
    const win = useWindowsStore.getState().windows[0];
    expect(win.title).toBe("file.tsx");
  });

  // ── close ───────────────────────────────────────────────────────────────────

  it("close — remove a janela pelo id", () => {
    open(WS, PATH_A);
    open(WS, PATH_B);
    useWindowsStore.getState().close(idOf(WS, PATH_A));
    const { windows } = useWindowsStore.getState();
    expect(windows).toHaveLength(1);
    expect(windows[0].id).toBe(idOf(WS, PATH_B));
  });

  it("close — id inexistente não altera lista", () => {
    open();
    useWindowsStore.getState().close("nao-existe");
    expect(useWindowsStore.getState().windows).toHaveLength(1);
  });

  // ── focus ───────────────────────────────────────────────────────────────────

  it("focus — traz a janela ao topo (zIndex maior que as demais)", () => {
    open(WS, PATH_A);
    open(WS, PATH_B);
    const idA = idOf(WS, PATH_A);
    useWindowsStore.getState().focus(idA);
    const { windows, topZ } = useWindowsStore.getState();
    const a = windows.find((w) => w.id === idA)!;
    expect(a.zIndex).toBe(topZ);
  });

  it("focus — não altera estado se já estiver no topo", () => {
    open(WS, PATH_A);
    const before = useWindowsStore.getState().topZ;
    useWindowsStore.getState().focus(idOf(WS, PATH_A));
    expect(useWindowsStore.getState().topZ).toBe(before);
  });

  // ── minimize / restore ──────────────────────────────────────────────────────

  it("minimize — marca a janela como minimized", () => {
    open();
    useWindowsStore.getState().minimize(idOf());
    expect(useWindowsStore.getState().windows[0].minimized).toBe(true);
  });

  it("restore — desmarca minimized e incrementa zIndex", () => {
    open();
    useWindowsStore.getState().minimize(idOf());
    const zBefore = useWindowsStore.getState().topZ;
    useWindowsStore.getState().restore(idOf());
    const win = useWindowsStore.getState().windows[0];
    expect(win.minimized).toBe(false);
    expect(win.zIndex).toBeGreaterThan(zBefore);
  });

  // ── setBounds ───────────────────────────────────────────────────────────────

  it("setBounds — atualiza x/y sem afetar outras propriedades", () => {
    open();
    useWindowsStore.getState().setBounds(idOf(), { x: 200, y: 150 });
    const win = useWindowsStore.getState().windows[0];
    expect(win.x).toBe(200);
    expect(win.y).toBe(150);
    expect(win.w).toBe(640); // inalterado
  });

  it("setBounds — atualiza w/h", () => {
    open();
    useWindowsStore.getState().setBounds(idOf(), { w: 800, h: 600 });
    const win = useWindowsStore.getState().windows[0];
    expect(win.w).toBe(800);
    expect(win.h).toBe(600);
  });

  it("setBounds — id inexistente não altera lista", () => {
    open();
    useWindowsStore.getState().setBounds("nao-existe", { x: 999 });
    expect(useWindowsStore.getState().windows[0].x).not.toBe(999);
  });

  // ── múltiplas janelas ────────────────────────────────────────────────────────

  it("múltiplos workspaces — janelas isoladas por workspaceId", () => {
    open("ws-A", PATH_A);
    open("ws-B", PATH_A);
    const { windows } = useWindowsStore.getState();
    expect(windows).toHaveLength(2);
    expect(windows[0].workspaceId).toBe("ws-A");
    expect(windows[1].workspaceId).toBe("ws-B");
  });
});
