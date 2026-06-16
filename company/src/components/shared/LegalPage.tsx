import { m } from "#/paraglide/messages";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";

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
    <Container size="prose" className="py-16">
      <PageHeader align="left" title={title} />
      <p className="mb-10 mt-3 text-sm text-muted-foreground">
        {m.legal_last_updated()} {lastUpdated}
      </p>
      <div className="prose prose-invert prose-sm max-w-none prose-headings:font-semibold prose-headings:text-foreground prose-p:text-foreground/90 prose-a:text-primary prose-li:text-foreground/90 prose-strong:text-foreground">
        {children}
      </div>
    </Container>
  );
}
