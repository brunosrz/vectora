/**
 * Setup global do vitest — company.
 *
 * 1. Estende `expect` com os matchers de DOM do @testing-library/jest-dom.
 * 2. Mocka `createServerFn` de `@tanstack/react-start`: fora do runtime real
 *    do Nitro/H3, `.handler(fn)` não tem como executar via RPC — o mock troca
 *    a cadeia `.validator(schema).handler(fn)` por uma função direta que roda
 *    a validação Zod de verdade (erros de schema continuam reais) e chama o
 *    handler com `{ data }`. Isso deixa toda a lógica de negócio dos arquivos
 *    em `src/server/fns/*.ts` testável por chamada direta
 *    (`await signIn({ data: {...} })`) sem precisar de um servidor de verdade.
 * 3. Substitui `globalThis.localStorage` por uma implementação em memória: o
 *    Node recente expõe seu próprio `localStorage` nativo (experimental, exige
 *    `--localstorage-file`), que sobrepõe o do jsdom e lança em qualquer
 *    acesso sem esse flag — `localStorage.clear()` explodia em todo teste que
 *    tocasse o storage, mesmo rodando em ambiente jsdom.
 */

import { afterEach, vi } from "vitest";

import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";

class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

Object.defineProperty(globalThis, "localStorage", {
  value: new MemoryStorage(),
  writable: true,
  configurable: true,
});

interface ServerFnChain {
  validator: (schema: { parse: (input: unknown) => unknown }) => ServerFnChain;
  handler: (
    fn: (ctx: { data: unknown }) => unknown,
  ) => (args?: { data?: unknown }) => unknown;
}

vi.mock("@tanstack/react-start", () => ({
  createServerFn: (_opts?: { method?: string }) => {
    let schema: { parse: (input: unknown) => unknown } | undefined;
    const chain: ServerFnChain = {
      validator(s) {
        schema = s;
        return chain;
      },
      handler(fn) {
        // async: garante que erro de validação Zod vire Promise rejeitada
        // (comportamento real de createServerFn), não um throw síncrono —
        // senão `expect(serverFn(...)).rejects...` explode antes do `.rejects`
        // conseguir interceptar, porque o throw acontece na avaliação do
        // argumento de `expect()`, fora de qualquer Promise.
        return async (args?: { data?: unknown }) => {
          const data = schema ? schema.parse(args?.data) : args?.data;
          return fn({ data });
        };
      },
    };
    return chain;
  },
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});
