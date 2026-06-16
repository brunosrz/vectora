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
// CSV parser — RFC 4180 (campos entre aspas podem conter vírgulas e quebras
// de linha; "" escapa aspas). Comentários: linhas iniciando com # fora de
// aspas são ignoradas.
// =============================================================================

/** Analisa o CSV inteiro em registros, respeitando campos multilinha. */
function parseCSV(csv: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  let fieldHasContent = false;
  let atRecordStart = true;
  let i = 0;
  const n = csv.length;

  const endField = () => {
    row.push(field);
    field = "";
    fieldHasContent = false;
  };
  const endRecord = () => {
    endField();
    rows.push(row);
    row = [];
    atRecordStart = true;
  };

  while (i < n) {
    const ch = csv[i];

    if (inQuotes) {
      if (ch === '"' && csv[i + 1] === '"') {
        field += '"';
        i += 2;
      } else if (ch === '"') {
        inQuotes = false;
        i++;
      } else {
        field += ch;
        i++;
      }
      continue;
    }

    // Comentário de linha inteira: '#' no início de um registro.
    if (atRecordStart && ch === "#") {
      const nl = csv.indexOf("\n", i);
      i = nl === -1 ? n : nl + 1;
      continue;
    }

    if (ch === '"' && !fieldHasContent) {
      inQuotes = true;
      fieldHasContent = true;
      atRecordStart = false;
      i++;
    } else if (ch === ",") {
      endField();
      atRecordStart = false;
      i++;
    } else if (ch === "\n") {
      endRecord();
      i++;
    } else if (ch === "\r") {
      i++;
    } else {
      field += ch;
      fieldHasContent = true;
      atRecordStart = false;
      i++;
    }
  }

  // Último registro sem newline final.
  if (fieldHasContent || field !== "" || row.length > 0) endRecord();
  return rows;
}

// =============================================================================
// Tipo interno e cache de traduções
// =============================================================================

type TranslationMap = Record<string, Record<Lang, string>>;

function buildTranslations(csv: string): TranslationMap {
  const map: TranslationMap = {};
  const rows = parseCSV(csv).filter((r) => r.length > 0 && r[0] !== "");
  if (rows.length === 0) return map;

  // Primeira linha = cabeçalho: key,en,es,pt,...
  const langs = rows[0].slice(1) as Lang[];

  for (const cols of rows.slice(1)) {
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
