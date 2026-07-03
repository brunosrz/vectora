import { describe, it, expect, beforeEach, vi } from "vitest";
import { track } from "./plausible";

beforeEach(() => {
  delete (window as { plausible?: unknown }).plausible;
});

describe("track", () => {
  it("chama window.plausible com props embrulhadas quando fornecidas", () => {
    const plausible = vi.fn();
    window.plausible = plausible;

    track("signup", { country: "BR" });

    expect(plausible).toHaveBeenCalledWith("signup", {
      props: { country: "BR" },
    });
  });

  it("chama window.plausible sem o wrapper 'props' quando não há props", () => {
    const plausible = vi.fn();
    window.plausible = plausible;

    track("gif_viewed");

    expect(plausible).toHaveBeenCalledWith("gif_viewed", undefined);
  });

  it("não lança quando window.plausible não existe (edge — self-hosted bloqueado/offline)", () => {
    expect(() => track("cancel")).not.toThrow();
  });
});
