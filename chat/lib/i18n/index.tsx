"use client";

/**
 * Vectora Chat — i18n (M6–M10)
 *
 * Infraestrutura de internacionalização sem dependências externas.
 *
 * Arquitetura:
 *   strings.csv.ts  → fonte de verdade (CSV: key,en,es,pt)
 *   index.tsx       → parser + I18nProvider + useT()
 *   settings-store  → campo language persiste a preferência do usuário
 *
 * Uso:
 *   const t = useT();
 *   t('header.new_chat')                   // → "New Chat" / "Nuevo Chat" / "Novo Chat"
 *   t('time.minutes_ago', { n: 5 })        // → "5 min ago" / "hace 5 min" / "há 5 min"
 *
 * Fallback: idioma não encontrado → inglês → chave literal (nunca quebra).
 */

import { useCallback, useEffect } from "react";
import type { ReactNode } from "react";
import { useSettingsStore, type Lang } from "@/lib/stores/settings-store";
import CSV from "./strings.csv";

// =============================================================================
// CSV parser — RFC 4180 single-line values
// =============================================================================

/** Analisa uma linha CSV respeitando campos entre aspas duplas. */
function parseCSVLine(line: string): string[] {
  const result: string[] = [];
  let i = 0;
  while (i <= line.length) {
    if (i === line.length) {
      // Linha terminou sem vírgula final → campo vazio no fim não é adicionado
      break;
    }
    if (line[i] === '"') {
      // Campo entre aspas
      let field = "";
      i++; // pula aspas de abertura
      while (i < line.length) {
        if (line[i] === '"' && line[i + 1] === '"') {
          field += '"';
          i += 2; // aspas escapadas ""
        } else if (line[i] === '"') {
          i++; // pula aspas de fechamento
          break;
        } else {
          field += line[i++];
        }
      }
      result.push(field);
      if (line[i] === ",") i++; // consome vírgula separadora
    } else {
      // Campo sem aspas — até a próxima vírgula
      const end = line.indexOf(",", i);
      if (end === -1) {
        result.push(line.slice(i));
        break;
      }
      result.push(line.slice(i, end));
      i = end + 1;
    }
  }
  return result;
}

// =============================================================================
// Tipo interno e cache de traduções
// =============================================================================

type TranslationMap = Record<string, Record<Lang, string>>;

function buildTranslations(csv: string): TranslationMap {
  const map: TranslationMap = {};
  const lines = csv
    .split("\n")
    .map((l) => l.trimEnd())
    .filter((l) => l.length > 0 && !l.startsWith("#"));

  if (lines.length === 0) return map;

  // Primeira linha = cabeçalho: key,en,es,pt,...
  const header = parseCSVLine(lines[0]);
  const langs = header.slice(1) as Lang[];

  for (const line of lines.slice(1)) {
    const cols = parseCSVLine(line);
    const key = cols[0];
    if (!key) continue;

    map[key] = {} as Record<Lang, string>;
    for (let idx = 0; idx < langs.length; idx++) {
      const lang = langs[idx];
      if (lang) map[key][lang] = cols[idx + 1] ?? "";
    }
  }
  return map;
}

// Parse executado uma única vez — resultado estático para toda a vida do módulo
const TRANSLATIONS: TranslationMap = buildTranslations(CSV);

// =============================================================================
// I18nProvider — atualiza document.documentElement.lang ao trocar idioma
// =============================================================================

interface I18nProviderProps {
  children: ReactNode;
}

export function I18nProvider({ children }: I18nProviderProps) {
  const language = useSettingsStore((s) => s.language);

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  return <>{children}</>;
}

// =============================================================================
// useT — hook principal de tradução
// =============================================================================

/**
 * Retorna função `t(key, params?)` para traduzir strings da UI.
 *
 * Fallback em cascata: idioma atual → inglês → chave literal.
 * Re-renderiza componentes apenas quando o idioma muda.
 */
export function useT(): (
  key: string,
  params?: Record<string, string | number>,
) => string {
  const language = useSettingsStore((s) => s.language);

  return useCallback(
    (key: string, params?: Record<string, string | number>): string =>
      translate(language, key, params),
    [language],
  );
}

// =============================================================================
// translate / t — tradução fora de componentes React (stores, utilitários)
// =============================================================================

function translate(
  language: Lang,
  key: string,
  params?: Record<string, string | number>,
): string {
  const entry = TRANSLATIONS[key];
  if (!entry) {
    if (process.env.NODE_ENV === "development") {
      console.warn(`[i18n] Missing key: "${key}"`);
    }
    return key;
  }

  // Fallback: idioma selecionado → inglês → chave
  const str = entry[language] ?? entry["en"] ?? key;

  if (!params) return str;
  // Interpolação simples: {varName}
  return str.replace(/\{(\w+)\}/g, (_, k: string) =>
    String(params[k] ?? `{${k}}`),
  );
}

/**
 * Tradução para contextos sem hooks (stores Zustand, handlers fora de React).
 * Lê o idioma atual direto do `settings-store` — não reage a mudanças, então
 * não deve ser usada para renderizar UI (use `useT` nesse caso).
 *
 * @example
 *   useToastStore.getState().error(t("workspaces.error.hydrate"));
 */
export function t(
  key: string,
  params?: Record<string, string | number>,
): string {
  return translate(useSettingsStore.getState().language, key, params);
}
