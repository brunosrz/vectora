import { describe, it, expect, afterEach } from "vitest";
import { detectOS } from "./downloads";

// detectOS mapeia o userAgent → plataforma para destacar o download recomendado.
function setUA(ua: string): void {
  Object.defineProperty(navigator, "userAgent", {
    value: ua,
    configurable: true,
  });
}

const original = navigator.userAgent;
afterEach(() => setUA(original));

describe("detectOS", () => {
  it("Windows", () => {
    setUA("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36");
    expect(detectOS()).toBe("windows");
  });

  it("macOS", () => {
    setUA("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605");
    expect(detectOS()).toBe("macos");
  });

  it("Linux", () => {
    setUA("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36");
    expect(detectOS()).toBe("linux");
  });

  it("userAgent desconhecido → null (edge)", () => {
    setUA("CoolBot/1.0 (+https://example.com/bot)");
    expect(detectOS()).toBeNull();
  });
});
