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
        className="cursor-pointer appearance-none rounded-md border border-brand-700 bg-brand-800 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:border-brand-500 focus:outline-none focus:ring-2 focus:ring-brand-500"
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
