import { getLocale, locales, setLocale } from "#/paraglide/runtime";
import { m } from "#/paraglide/messages";

const LOCALE_LABELS: Partial<Record<string, string>> = {
  pt: "PT",
  en: "EN",
  es: "ES",
  fr: "FR",
  it: "IT",
  de: "DE",
  ru: "RU",
};

export default function LocaleSwitcher() {
  const current = getLocale();

  return (
    <div className="relative">
      <select
        value={current}
        onChange={(e) => setLocale(e.target.value as (typeof locales)[number])}
        className="h-8 cursor-pointer appearance-none rounded-lg border border-border bg-card px-3 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus:outline-none focus:ring-2 focus:ring-primary"
        aria-label={m.language_label()}
      >
        {locales.map((locale) => (
          <option key={locale} value={locale}>
            {LOCALE_LABELS[locale] ?? locale.toUpperCase()}
          </option>
        ))}
      </select>
    </div>
  );
}
