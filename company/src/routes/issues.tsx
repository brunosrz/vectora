import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import Turnstile from "#/components/shared/Turnstile";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";
import {
  submitIssue,
  listOpenIssues,
  type IssueListItem,
} from "#/server/fns/issues";
import { toast } from "sonner";

export const Route = createFileRoute("/issues")({
  head: () => ({
    meta: [
      { title: m.page_issues_title() },
      {
        property: "og:image",
        content: `/api/og?title=${encodeURIComponent(m.page_issues_title())}&desc=${encodeURIComponent("Reporte bugs, envie feedback ou sugira features para o Vectora.")}`,
      },
    ],
  }),
  loader: async () => ({ issues: await listOpenIssues() }),
  component: IssuesPage,
});

const CATEGORIES = ["bug", "feedback", "feature"] as const;
type Category = (typeof CATEGORIES)[number];

const CATEGORY_LABELS: Record<Category, string> = {
  bug: "Bug",
  feedback: "Feedback",
  feature: "Feature request",
};

function IssueForm() {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<Category>("bug");
  const [description, setDescription] = useState("");
  const [email, setEmail] = useState("");
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () =>
      submitIssue({
        data: {
          title,
          category,
          description,
          email,
          turnstileToken: turnstileToken!,
        },
      }),
    onSuccess: () => {
      toast.success(m.issues_success());
      setTitle("");
      setDescription("");
      setEmail("");
      setTurnstileToken(null);
    },
    onError: () => toast.error(m.error_generic()),
  });

  const canSubmit =
    title.length >= 3 &&
    description.length >= 10 &&
    turnstileToken !== null &&
    !mutation.isPending;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) mutation.mutate();
      }}
      className="space-y-5"
    >
      <div>
        <label className="mb-1.5 block text-sm font-medium text-foreground/90">
          {m.issues_title_label()}
        </label>
        <input
          type="text"
          required
          minLength={3}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-foreground/90">
          {m.issues_category_label()}
        </label>
        <div className="flex gap-2">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              type="button"
              onClick={() => setCategory(c)}
              className={`rounded-lg border px-3 py-1.5 text-sm transition-all ${
                category === c
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-border text-muted-foreground hover:text-foreground/90"
              }`}
            >
              {CATEGORY_LABELS[c]}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-foreground/90">
          {m.issues_desc_label()}
        </label>
        <textarea
          required
          minLength={10}
          rows={5}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full resize-none rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-foreground/90">
          {m.issues_email_label()}
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="opcional — para receber atualizações"
          className="w-full rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:border-primary transition-colors"
        />
      </div>

      <Turnstile onSuccess={setTurnstileToken} />

      <button
        type="submit"
        disabled={!canSubmit}
        className="rounded-xl bg-primary px-6 py-2.5 text-sm font-semibold text-primary-foreground shadow shadow-primary/25 transition-all hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {mutation.isPending ? m.form_submitting() : m.issues_submit()}
      </button>
    </form>
  );
}

function IssuesList({ issues }: { issues: IssueListItem[] }) {
  return (
    <section className="mt-14">
      <h2 className="mb-4 text-lg font-semibold text-foreground">
        {m.issues_list_title()}
      </h2>
      {issues.length === 0 ? (
        <p className="text-sm text-muted-foreground">{m.issues_list_empty()}</p>
      ) : (
        <ul className="space-y-3">
          {issues.map((issue) => (
            <li
              key={issue.id}
              className="rounded-xl border border-border bg-card/40 px-4 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <span className="text-sm font-medium text-foreground">
                  {issue.title}
                </span>
                <span className="shrink-0 rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
                  {CATEGORY_LABELS[issue.category]}
                </span>
              </div>
              {issue.description && (
                <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                  {issue.description}
                </p>
              )}
              <time className="mt-1.5 block text-[11px] text-muted-foreground/70">
                {new Date(issue.created_at).toLocaleDateString()}
              </time>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function IssuesPage() {
  const { issues } = Route.useLoaderData();
  return (
    <Container size="prose" className="py-16">
      <div className="mb-10">
        <PageHeader
          align="left"
          title={m.page_issues_title()}
          subtitle={m.issues_subtitle()}
        />
      </div>
      <IssueForm />
      <IssuesList issues={issues} />
    </Container>
  );
}
