import { m } from "#/paraglide/messages";

interface LegalPageProps {
  title: string;
  lastUpdated: string;
  children: React.ReactNode;
}

export default function LegalPage({
  title,
  lastUpdated,
  children,
}: LegalPageProps) {
  return (
    <div className="mx-auto max-w-3xl px-4 py-16 sm:px-6 lg:px-8">
      <h1 className="mb-2 text-3xl font-semibold text-white">{title}</h1>
      <p className="mb-10 text-sm text-slate-500">
        {m.legal_last_updated()} {lastUpdated}
      </p>
      <div className="prose prose-invert prose-sm max-w-none prose-headings:font-semibold prose-headings:text-white prose-p:text-slate-300 prose-a:text-brand-400 prose-li:text-slate-300 prose-strong:text-white">
        {children}
      </div>
    </div>
  );
}
