import { getLocale, locales, setLocale } from "#/paraglide/runtime";

const LOCALE_LABELS: Record<string, string> = {
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
        className="cursor-pointer appearance-none rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-foreground/90 transition-colors hover:border-primary focus:outline-none focus:ring-2 focus:ring-primary"
        aria-label="Select language"
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
