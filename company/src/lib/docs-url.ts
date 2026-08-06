import { getLocale } from "#/paraglide/runtime";

/**
 * docs.vectora.company (Hugo) só publica en/pt/es — locales do site
 * (fr/it/de/ru) sem página própria caem em en, o default do Hugo.
 * `defaultContentLanguageInSubdir = true` no hugo.toml: todo idioma,
 * incluindo o default, vive sob um prefixo (/en, /pt, /es).
 */
const DOCS_LOCALES = new Set(["en", "pt", "es"]);

export function getDocsUrl(path = ""): string {
  const locale = getLocale();
  const docsLocale = DOCS_LOCALES.has(locale) ? locale : "en";
  const suffix = path ? `/${path.replace(/^\/+/, "")}` : "";
  return `https://docs.vectora.company/${docsLocale}${suffix}`;
}
