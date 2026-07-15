import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { m } from "#/paraglide/messages";
import { getIssueAdmin, respondToIssue } from "#/server/fns/admin";

export const Route = createFileRoute("/admin/issues/$issueId")({
  component: AdminIssueDetailPage,
});

const CATEGORIES = ["bug", "feedback", "feature"] as const;
type Category = (typeof CATEGORIES)[number];

const CATEGORY_LABELS: Record<Category, string> = {
  bug: "Bug",
  feedback: "Feedback",
  feature: "Feature request",
};

function AdminIssueDetailPage() {
  const { issueId } = Route.useParams();
  const queryClient = useQueryClient();
  const { data: issue, isLoading } = useQuery({
    queryKey: ["admin-issue", issueId],
    queryFn: () => getIssueAdmin({ data: { id: issueId } }),
  });

  const [response, setResponse] = useState("");
  const [resolve, setResolve] = useState(true);

  const respondMutation = useMutation({
    mutationFn: () =>
      respondToIssue({ data: { id: issueId, response, resolve } }),
    onSuccess: () => {
      toast.success(m.admin_issue_response_sent());
      setResponse("");
      queryClient.invalidateQueries({ queryKey: ["admin-issue", issueId] });
      queryClient.invalidateQueries({ queryKey: ["admin-issues"] });
    },
    onError: () => toast.error(m.error_generic()),
  });

  if (isLoading) {
    return <div className="h-40 rounded-xl bg-card/30 animate-pulse" />;
  }

  if (!issue) {
    return (
      <div>
        <Link
          to="/admin/issues"
          className="text-sm text-primary hover:underline"
        >
          {m.issues_detail_back()}
        </Link>
        <p className="mt-6 text-sm text-muted-foreground">
          {m.issues_detail_not_found()}
        </p>
      </div>
    );
  }

  return (
    <div>
      <Link to="/admin/issues" className="text-sm text-primary hover:underline">
        {m.issues_detail_back()}
      </Link>

      <h1 className="mt-4 mb-2 text-lg font-semibold text-foreground">
        {issue.title}
      </h1>
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
          {CATEGORY_LABELS[issue.category]}
        </span>
        <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
          {issue.status === "resolved"
            ? m.issues_status_resolved()
            : m.issues_status_open()}
        </span>
        {issue.email && (
          <span className="rounded-full border border-border px-2 py-0.5 text-[11px] text-muted-foreground">
            {issue.email}
          </span>
        )}
      </div>

      {issue.description && (
        <p className="mb-4 whitespace-pre-wrap text-sm text-foreground/90">
          {issue.description}
        </p>
      )}

      {issue.files.length > 0 && (
        <p className="mb-4 flex flex-wrap items-center gap-2 text-[11px]">
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

      {issue.response && (
        <div className="mb-4 rounded-xl border border-border bg-card/30 p-4">
          <p className="mb-1 text-xs font-medium text-muted-foreground">
            {m.admin_issue_response_existing()}
          </p>
          <p className="whitespace-pre-wrap text-sm text-foreground/90">
            {issue.response}
          </p>
        </div>
      )}

      <div className="max-w-xl space-y-3 rounded-xl border border-border bg-card/30 p-4">
        <label
          htmlFor="issue-response"
          className="block text-xs font-medium text-muted-foreground"
        >
          {m.admin_issue_response_label()}
        </label>
        <textarea
          id="issue-response"
          rows={4}
          value={response}
          onChange={(e) => setResponse(e.target.value)}
          placeholder={m.admin_issue_response_placeholder()}
          className="w-full resize-none rounded-lg border border-border bg-background px-3 py-2 text-sm outline-none focus:border-primary"
        />
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={resolve}
            onChange={(e) => setResolve(e.target.checked)}
          />
          {m.admin_issue_mark_resolved()}
        </label>
        <button
          onClick={() => respondMutation.mutate()}
          disabled={response.trim().length < 3 || respondMutation.isPending}
          className="w-full rounded-lg bg-primary py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-all"
        >
          {respondMutation.isPending
            ? m.form_submitting()
            : m.admin_issue_response_submit()}
        </button>
      </div>
    </div>
  );
}
