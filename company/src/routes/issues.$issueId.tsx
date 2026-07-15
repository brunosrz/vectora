import { createFileRoute, Link } from "@tanstack/react-router";
import { m } from "#/paraglide/messages";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";
import { getIssue } from "#/server/fns/issues";

export const Route = createFileRoute("/issues/$issueId")({
  head: () => ({
    meta: [{ name: "robots", content: "noindex, nofollow" }],
  }),
  loader: async ({ params }) => ({
    issue: await getIssue({ data: { id: params.issueId } }),
  }),
  component: IssueDetailPage,
});

const CATEGORIES = ["bug", "feedback", "feature"] as const;
type Category = (typeof CATEGORIES)[number];

const CATEGORY_LABELS: Record<Category, string> = {
  bug: "Bug",
  feedback: "Feedback",
  feature: "Feature request",
};

function IssueDetailPage() {
  const { issue } = Route.useLoaderData();

  if (!issue) {
    return (
      <Container size="prose" className="py-16">
        <Link to="/issues" className="text-sm text-primary hover:underline">
          {m.issues_detail_back()}
        </Link>
        <p className="mt-6 text-sm text-muted-foreground">
          {m.issues_detail_not_found()}
        </p>
      </Container>
    );
  }

  return (
    <Container size="prose" className="py-16">
      <Link to="/issues" className="text-sm text-primary hover:underline">
        {m.issues_detail_back()}
      </Link>

      <div className="mt-6 mb-10">
        <PageHeader align="left" title={issue.title} />
      </div>

      <div className="rounded-xl border border-border bg-card/40 px-5 py-4">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
            {CATEGORY_LABELS[issue.category]}
          </span>
          <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
            {issue.status === "resolved"
              ? m.issues_status_resolved()
              : m.issues_status_open()}
          </span>
        </div>

        {issue.description && (
          <p className="mt-4 whitespace-pre-wrap text-sm text-foreground/90">
            {issue.description}
          </p>
        )}

        {issue.files.length > 0 && (
          <p className="mt-4 flex flex-wrap items-center gap-2 text-[11px]">
            <span className="text-muted-foreground/70">
              {m.issues_attachments()}:
            </span>
            {issue.files.map((url, index) => (
              <a
                key={url}
                href={url}
                target="_blank"
                rel="noreferrer"
                className="text-primary hover:underline"
              >
                #{index + 1}
              </a>
            ))}
          </p>
        )}

        <time className="mt-4 block text-[11px] text-muted-foreground/70">
          {new Date(issue.created_at).toLocaleDateString()}
        </time>
      </div>
    </Container>
  );
}
