// @vitest-environment jsdom
/**
 * useSlotOverlay — reposiciona o overlay pro retângulo do slot ativo sem
 * desmontar nada; quando não há slot ativo (null), só esconde o overlay.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, cleanup, render } from "@testing-library/react";
import { useRef, useState } from "react";

import { useSlotOverlay } from "../use-slot-overlay";

let observers: MockResizeObserver[] = [];

class MockResizeObserver {
  callback: ResizeObserverCallback;
  observed: Element[] = [];
  disconnected = false;

  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
    observers.push(this);
  }

  observe(target: Element) {
    this.observed.push(target);
  }

  unobserve() {}

  disconnect() {
    this.disconnected = true;
  }
}

function rect(top: number, left: number, width: number, height: number) {
  return {
    top,
    left,
    width,
    height,
    right: left + width,
    bottom: top + height,
    x: left,
    y: top,
    toJSON: () => ({}),
  } as DOMRect;
}

beforeEach(() => {
  observers = [];
  vi.stubGlobal("ResizeObserver", MockResizeObserver);
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

function Sonda({ active }: { active: "a" | "b" | null }) {
  const anchorRef = useRef<HTMLDivElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [slotAEl, setSlotAEl] = useState<HTMLDivElement | null>(null);
  const [slotBEl, setSlotBEl] = useState<HTMLDivElement | null>(null);

  const slotEl = active === "a" ? slotAEl : active === "b" ? slotBEl : null;
  useSlotOverlay(slotEl, overlayRef, anchorRef);

  return (
    <div ref={anchorRef} data-testid="anchor">
      <div
        ref={overlayRef}
        data-testid="overlay"
        style={{ position: "absolute" }}
      />
      {active === "a" && <div ref={setSlotAEl} data-testid="slot-a" />}
      {active === "b" && <div ref={setSlotBEl} data-testid="slot-b" />}
    </div>
  );
}

describe("useSlotOverlay", () => {
  it("posiciona o overlay no retângulo do slot ativo, e reposiciona ao trocar de slot", () => {
    const { container, rerender } = render(<Sonda active="a" />);

    const anchor = container.querySelector<HTMLElement>(
      '[data-testid="anchor"]',
    )!;
    const overlay = container.querySelector<HTMLElement>(
      '[data-testid="overlay"]',
    )!;
    const slotA = container.querySelector<HTMLElement>(
      '[data-testid="slot-a"]',
    )!;

    anchor.getBoundingClientRect = () => rect(0, 0, 1000, 800);
    slotA.getBoundingClientRect = () => rect(10, 20, 300, 400);

    // Simula o ResizeObserver disparando (mesmo padrão de
    // use-element-width.test.tsx) — o sync do mount já rodou com rects
    // zeradas (jsdom não faz layout); isso força o sync de novo já com os
    // retângulos mockados.
    const observerA = observers[observers.length - 1];
    act(() => {
      observerA?.callback([], observerA as unknown as ResizeObserver);
    });

    expect(overlay.style.top).toBe("10px");
    expect(overlay.style.left).toBe("20px");
    expect(overlay.style.width).toBe("300px");
    expect(overlay.style.height).toBe("400px");
    expect(overlay.style.visibility).toBe("visible");

    rerender(<Sonda active="b" />);
    const slotB = container.querySelector<HTMLElement>(
      '[data-testid="slot-b"]',
    )!;
    slotB.getBoundingClientRect = () => rect(50, 60, 500, 600);

    const observerB = observers[observers.length - 1];
    act(() => {
      observerB?.callback([], observerB as unknown as ResizeObserver);
    });

    expect(overlay.style.top).toBe("50px");
    expect(overlay.style.left).toBe("60px");
    expect(overlay.style.width).toBe("500px");
    expect(overlay.style.height).toBe("600px");
  });

  it("caso de borda: sem slot ativo (null), o overlay só fica invisível, sem lançar", () => {
    const { container } = render(<Sonda active={null} />);

    const overlay = container.querySelector<HTMLElement>(
      '[data-testid="overlay"]',
    )!;

    expect(overlay.style.visibility).toBe("hidden");
  });
});
