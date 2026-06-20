/**
 * Setup global do vitest.
 *
 * 1. Estende `expect` com os matchers de DOM do @testing-library/jest-dom
 *    (toBeInTheDocument, toBeEmptyDOMElement, etc.).
 *
 * 2. Instala um localStorage/sessionStorage in-memory. No Node 22+ existe um
 *    `localStorage` nativo experimental que fica `undefined` sem
 *    `--localstorage-file` e sombreia o do jsdom — o que quebra o zustand
 *    persist e o paraglide (`getLocale()` lê localStorage). O polyfill garante
 *    um Storage funcional em ambos os ambientes (node e jsdom).
 */

import { afterEach } from "vitest";
// Import de efeito colateral: registra os matchers de DOM no `expect`.
// eslint-disable-next-line import/no-unassigned-import
import "@testing-library/jest-dom/vitest";

// monaco-editor chama document.queryCommandSupported() no carregamento —
// jsdom não implementa esse método legado, então precisamos de um stub.
if (typeof document !== "undefined" && !document.queryCommandSupported) {
  document.queryCommandSupported = () => false;
}

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
  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
  removeItem(key: string): void {
    this.store.delete(key);
  }
  key(index: number): string | null {
    return [...this.store.keys()][index] ?? null;
  }
}

const localStoragePolyfill = new MemoryStorage();
const sessionStoragePolyfill = new MemoryStorage();

for (const [name, value] of [
  ["localStorage", localStoragePolyfill],
  ["sessionStorage", sessionStoragePolyfill],
] as const) {
  Object.defineProperty(globalThis, name, {
    value,
    configurable: true,
    writable: true,
  });
}

// Isola os testes: limpa o storage entre cada um (evita vazamento de chaves
// persistidas por stores zustand entre testes do mesmo arquivo).
afterEach(() => {
  localStoragePolyfill.clear();
  sessionStoragePolyfill.clear();
});
