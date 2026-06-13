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
      <h1 className="mb-2 text-3xl font-semibold text-foreground">{title}</h1>
      <p className="mb-10 text-sm text-muted-foreground">
        {m.legal_last_updated()} {lastUpdated}
      </p>
      <div className="prose prose-invert prose-sm max-w-none prose-headings:font-semibold prose-headings:text-foreground prose-p:text-foreground/90 prose-a:text-primary prose-li:text-foreground/90 prose-strong:text-foreground">
        {children}
      </div>
    </div>
  );
}
