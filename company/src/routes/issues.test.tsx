// @vitest-environment jsdom
/**
 * /issues — errorComponent: uma falha no loader (ex.: coluna ausente no D1
 * de produção, incidente já ocorrido nesse projeto) não pode deixar a
 * página em branco sem explicação. Cobre a lacuna: antes desta mudança não
 * existia nenhum teste pra esse caminho.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";

import { IssuesErrorComponent } from "./issues";

vi.mock("#/paraglide/messages", () => ({
  m: new Proxy(
    {},
    {
      get:
        (_t, prop) =>
        (..._args: unknown[]) =>
          String(prop),
    },
  ),
}));

describe("/issues errorComponent", () => {
  it("renderiza uma mensagem de erro amigável quando o loader falha", () => {
    render(<IssuesErrorComponent />);

    expect(screen.getByText("error_generic")).toBeTruthy();
  });
});
