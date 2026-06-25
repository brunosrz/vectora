// @vitest-environment jsdom
/**
 * TDD — Render Hints Novos (FASE 5.4)
 *
 * Verifica que ToolCallRenderer despacha para renderers corretos via registry.
 */

import { describe, expect, it, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { ToolCallRenderer } from "../tool-call-renderer";
import type { ToolCall } from "@/lib/types";

afterEach(cleanup);

function makeTool(overrides: Partial<ToolCall> = {}): ToolCall {
  return {
    id: "tc-1",
    name: "test_tool",
    args: {},
    ...overrides,
  };
}

describe("Render Hints — registry dispatch", () => {
  it("renders image_preview hint with an img element", () => {
    const tool = makeTool({
      renderHint: "image_preview",
      output: { url: "https://example.com/img.png", alt: "screenshot" },
    });
    const { container } = render(
      <ToolCallRenderer tool={tool} isStreaming={false} />,
    );
    const img = container.querySelector("img");
    expect(img).not.toBeNull();
  });

  it("renders thinking_step hint with accordion structure", () => {
    const tool = makeTool({
      renderHint: "thinking_step",
      output: { thought: "Analisando o código...", thought_number: 1, total_thoughts: 3, is_final: false },
    });
    render(<ToolCallRenderer tool={tool} isStreaming={false} />);
    expect(screen.getByText(/Analisando o código/i)).toBeDefined();
  });

  it("renders json hint as fallback for unknown output", () => {
    const tool = makeTool({
      renderHint: "json",
      output: { status: "ok" },
    });
    render(<ToolCallRenderer tool={tool} isStreaming={false} />);
    // Json viewer shows "Ver output" summary
    expect(screen.getByText(/Ver output/i)).toBeDefined();
  });

  it("falls back to json renderer for unknown renderHint", () => {
    const tool = makeTool({
      renderHint: "unknown_hint" as any,
      output: { data: 42 },
    });
    render(<ToolCallRenderer tool={tool} isStreaming={false} />);
    expect(screen.getByText(/Ver output/i)).toBeDefined();
  });
});
