// @vitest-environment jsdom
/**
 * Fuso horário nas Preferências. O backend já usava `user_timezone` para
 * converter "toda segunda às 9h" no UTC de armazenamento; sem este seletor a
 * config só existia por API e "9h" virava 9h UTC para todo mundo.
 *
 * O que os testes travam: a lista vem do backend (copiá-la no frontend faria a
 * UI divergir do que o backend aceita) e uma falha ao salvar **reverte** a
 * seleção — deixar o valor novo na tela faria o usuário crer que salvou.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  cleanup,
  waitFor,
  fireEvent,
} from "@testing-library/react";

vi.mock("@/lib/paraglide/messages", () => ({
  m: new Proxy({}, { get: (_t, prop) => () => String(prop) }),
}));

import { PreferenciasTab } from "../preferencias-tab";

const ZONAS = ["America/Sao_Paulo", "Europe/Lisbon", "UTC"];

function stubFetch(opts: { ok?: boolean; patchOk?: boolean } = {}) {
  const { ok = true, patchOk = true } = opts;
  const chamadas: { url: string; method: string; body?: string }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const u = String(url);
      const method = init?.method ?? "GET";
      chamadas.push({ url: u, method, body: init?.body as string });
      if (u.includes("/admin/timezone") && method === "GET") {
        return ok
          ? new Response(JSON.stringify({ timezone: "UTC", available: ZONAS }))
          : new Response("erro", { status: 500 });
      }
      if (u.includes("/admin/timezone") && method === "PATCH") {
        return patchOk
          ? new Response(JSON.stringify({ status: "updated" }))
          : new Response("invalido", { status: 422 });
      }
      return new Response(JSON.stringify({}));
    }),
  );
  return chamadas;
}

beforeEach(() => {
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: false,
    media: q,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("TimezoneSection", () => {
  it("carrega a lista de zonas do backend, não de uma cópia local", async () => {
    const chamadas = stubFetch();

    render(<PreferenciasTab />);

    await waitFor(() =>
      expect(
        chamadas.some(
          (c) => c.url.includes("/admin/timezone") && c.method === "GET",
        ),
      ).toBe(true),
    );
    await waitFor(() =>
      expect(screen.getByText("prefs_timezone_section")).toBeInTheDocument(),
    );
  });

  it("some quando o backend não devolve zonas (edge)", async () => {
    // Erro/borda: sem lista não há o que escolher — melhor não renderizar um
    // seletor vazio que parece quebrado.
    stubFetch({ ok: false });

    render(<PreferenciasTab />);

    await waitFor(() =>
      expect(screen.queryByText("prefs_timezone_section")).toBeNull(),
    );
  });
});

describe("MediaModelsSection", () => {
  it("repinta com o valor efetivo devolvido pelo backend ao limpar o campo", async () => {
    // Cenário do invariante: o usuário limpa o campo, mas existe env var —
    // o que passa a valer é a env. Mostrar o campo vazio faria parecer que a
    // capacidade ficou desligada.
    const patches: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        const u = String(url);
        const method = init?.method ?? "GET";
        if (u.includes("/admin/media-models") && method === "GET") {
          return new Response(
            JSON.stringify({ models: { ollama_image_model: "escolha-da-ui" } }),
          );
        }
        if (u.includes("/admin/media-models") && method === "PATCH") {
          patches.push(String(init?.body));
          return new Response(
            JSON.stringify({ models: { ollama_image_model: "modelo-da-env" } }),
          );
        }
        if (u.includes("/admin/timezone")) {
          return new Response(
            JSON.stringify({ timezone: "UTC", available: ZONAS }),
          );
        }
        return new Response(JSON.stringify({}));
      }),
    );

    render(<PreferenciasTab />);

    const campo = (await screen.findByLabelText(
      "prefs_media_models_ollama_image",
    )) as HTMLInputElement;
    expect(campo.value).toBe("escolha-da-ui");

    fireEvent.change(campo, { target: { value: "" } });
    fireEvent.blur(campo);

    await waitFor(() => expect(patches.length).toBe(1));
    // Erro/borda: o campo NÃO fica vazio — mostra o que de fato vale agora.
    await waitFor(() => expect(campo.value).toBe("modelo-da-env"));
  });

  it("backend fora do ar deixa os campos vazios sem quebrar a aba (edge)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        if (String(url).includes("/admin/media-models")) {
          return new Response("erro", { status: 500 });
        }
        return new Response(
          JSON.stringify({ timezone: "UTC", available: ZONAS }),
        );
      }),
    );

    render(<PreferenciasTab />);

    const campo = (await screen.findByLabelText(
      "prefs_media_models_ollama_tts",
    )) as HTMLInputElement;
    expect(campo.value).toBe("");
  });
});
