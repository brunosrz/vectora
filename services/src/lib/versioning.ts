/**
 * Compara duas strings de versão semver "solto" — não valida formato, só
 * compara segmento a segmento numericamente quando possível, caindo pra
 * comparação lexicográfica em segmentos não-numéricos. Suficiente pro caso
 * de uso (versões publicadas pelo próprio schema, não input arbitrário de
 * terceiro sem validação nenhuma).
 */
export function compareVersions(a: string, b: string): number {
  const as = a.split(".");
  const bs = b.split(".");
  const len = Math.max(as.length, bs.length);
  for (let i = 0; i < len; i++) {
    const av = as[i] ?? "0";
    const bv = bs[i] ?? "0";
    const an = Number(av);
    const bn = Number(bv);
    if (!Number.isNaN(an) && !Number.isNaN(bn)) {
      if (an !== bn) return an - bn;
    } else if (av !== bv) {
      return av < bv ? -1 : 1;
    }
  }
  return 0;
}

interface Versioned {
  package_name: string | null;
  version: string;
}

/**
 * Agrupa por `package_name`: mantém só a versão mais recente de cada
 * grupo. Linhas sem `package_name` (registros legados, pré-versionamento)
 * passam individualmente — não têm conceito de "outra versão" pra colapsar.
 */
export function latestPerPackage<T extends Versioned>(rows: T[]): T[] {
  const byPackage = new Map<string, T>();
  const standalone: T[] = [];
  for (const row of rows) {
    if (!row.package_name) {
      standalone.push(row);
      continue;
    }
    const current = byPackage.get(row.package_name);
    if (!current || compareVersions(row.version, current.version) > 0) {
      byPackage.set(row.package_name, row);
    }
  }
  return [...standalone, ...byPackage.values()];
}
