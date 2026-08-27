// @vitest-environment jsdom
/**
 * /features — cada feature listada precisa de título, resumo E descrição
 * completa reais (nenhum vazio) e id único, senão o accordion quebra
 * silenciosamente (duas entradas com o mesmo `value` do Radix Accordion
 * colidem) ou mostra uma linha em branco pro usuário.
 */
import { describe, it, expect, vi } from "vitest";

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

import { getFeatureCategories } from "./features";

describe("getFeatureCategories", () => {
  it("tem pelo menos 4 categorias, cada uma com pelo menos 1 feature", () => {
    const categories = getFeatureCategories();
    expect(categories.length).toBeGreaterThanOrEqual(4);
    for (const category of categories) {
      expect(category.items.length).toBeGreaterThan(0);
    }
  });

  it("erro/borda: nenhuma feature tem título, resumo ou descrição vazios", () => {
    const categories = getFeatureCategories();
    const allItems = categories.flatMap((c) => c.items);
    expect(allItems.length).toBeGreaterThan(0);
    for (const item of allItems) {
      expect(item.title.trim().length).toBeGreaterThan(0);
      expect(item.summary.trim().length).toBeGreaterThan(0);
      expect(item.description.trim().length).toBeGreaterThan(0);
    }
  });

  it("erro/borda: todos os ids de feature são únicos (accordion Radix colide em duplicata)", () => {
    const categories = getFeatureCategories();
    const ids = categories.flatMap((c) => c.items.map((i) => i.id));
    expect(new Set(ids).size).toBe(ids.length);
  });
});
