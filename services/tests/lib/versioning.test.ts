import { describe, it, expect } from "vitest";
import { compareVersions, latestPerPackage } from "../../src/lib/versioning";

describe("compareVersions", () => {
  it("compara segmentos numéricos por valor, não lexicograficamente", () => {
    // "0.1.9" < "0.1.10" numericamente, mas ">" lexicograficamente.
    expect(compareVersions("0.1.9", "0.1.10")).toBeLessThan(0);
    expect(compareVersions("0.1.10", "0.1.9")).toBeGreaterThan(0);
  });

  it("versões idênticas comparam igual (0)", () => {
    expect(compareVersions("1.2.3", "1.2.3")).toBe(0);
  });

  it("trata segmentos ausentes como 0 — 1.2 == 1.2.0", () => {
    expect(compareVersions("1.2", "1.2.0")).toBe(0);
    expect(compareVersions("1.2", "1.2.1")).toBeLessThan(0);
  });

  it("cai pra comparação lexicográfica em segmentos não-numéricos", () => {
    expect(compareVersions("1.0.0-beta", "1.0.0-alpha")).toBeGreaterThan(0);
  });

  it("erro de borda — string vazia não quebra, trata como 0", () => {
    expect(compareVersions("", "1.0.0")).toBeLessThan(0);
    expect(compareVersions("", "")).toBe(0);
  });
});

describe("latestPerPackage", () => {
  interface Row {
    package_name: string | null;
    version: string;
    id: string;
  }

  it("mantém só a versão mais recente por package_name", () => {
    const rows: Row[] = [
      { id: "a1", package_name: "pkg-a", version: "1.0.0" },
      { id: "a2", package_name: "pkg-a", version: "2.0.0" },
      { id: "a3", package_name: "pkg-a", version: "1.5.0" },
    ];
    const result = latestPerPackage(rows);
    expect(result).toHaveLength(1);
    expect(result[0]!.id).toBe("a2");
  });

  it("agrupa múltiplos pacotes independentemente", () => {
    const rows: Row[] = [
      { id: "a1", package_name: "pkg-a", version: "1.0.0" },
      { id: "b1", package_name: "pkg-b", version: "3.0.0" },
      { id: "a2", package_name: "pkg-a", version: "2.0.0" },
    ];
    const result = latestPerPackage(rows);
    expect(result).toHaveLength(2);
    expect(result.map((r) => r.id).sort()).toEqual(["a2", "b1"]);
  });

  it("linhas sem package_name passam individualmente, sem colapsar", () => {
    const rows: Row[] = [
      { id: "s1", package_name: null, version: "1.0.0" },
      { id: "s2", package_name: null, version: "1.0.0" },
    ];
    const result = latestPerPackage(rows);
    expect(result).toHaveLength(2);
  });

  it("erro de borda — lista vazia devolve lista vazia", () => {
    expect(latestPerPackage([])).toEqual([]);
  });

  it("erro de borda — mistura standalone e agrupado no mesmo lote", () => {
    const rows: Row[] = [
      { id: "s1", package_name: null, version: "1.0.0" },
      { id: "a1", package_name: "pkg-a", version: "1.0.0" },
      { id: "a2", package_name: "pkg-a", version: "1.1.0" },
    ];
    const result = latestPerPackage(rows);
    expect(result).toHaveLength(2);
    expect(result.map((r) => r.id).sort()).toEqual(["a2", "s1"]);
  });
});
