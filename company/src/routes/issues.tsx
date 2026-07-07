import { createFileRoute } from "@tanstack/react-router";
import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Paperclip, X } from "lucide-react";
import { m } from "#/paraglide/messages";
import Turnstile from "#/components/shared/Turnstile";
import Container from "#/components/shared/Container";
import PageHeader from "#/components/shared/PageHeader";
import {
  submitIssue,
  submitIssueWithFiles,
  listOpenIssues,
} from "#/server/fns/issues";
import type { IssueListItem } from "#/server/fns/issues";
import {
  ISSUE_FILE_ACCEPT,
  MAX_ISSUE_FILES,
  isVideoType,
  readVideoDuration,
  validateIssueFile,
} from "#/lib/issue-files";
import type { IssueFileError } from "#/lib/issue-files";
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

const FILE_ERROR_MESSAGES: Record<IssueFileError, () => string> = {
  invalid_type: () => m.issues_file_error_invalid_type(),
  too_large: () => m.issues_file_error_too_large(),
  video_too_long: () => m.issues_file_error_video_too_long(),
  too_many: () => m.issues_file_error_too_many(),
};

function IssueForm() {
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<Category>("bug");
  const [description, setDescription] = useState("");
  const [email, setEmail] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function addFiles(incoming: FileList | null) {
    if (!incoming) return;
    const next = [...files];
    for (const file of Array.from(incoming)) {
      if (next.length >= MAX_ISSUE_FILES) {
        toast.error(FILE_ERROR_MESSAGES.too_many());
        break;
      }
      let duration: number | undefined;
      if (isVideoType(file.type)) {
        duration = await readVideoDuration(file).catch(() => undefined);
      }
      const error = validateIssueFile(file, duration);
      if (error) {
        toast.error(`${file.name}: ${FILE_ERROR_MESSAGES[error]()}`);
        continue;
      }
      next.push(file);
    }
    setFiles(next);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const mutation = useMutation({
    mutationFn: () => {
      if (files.length === 0) {
        return submitIssue({
          data: {
            title,
            category,
            description,
            email,
            turnstileToken: turnstileToken!,
          },
        });
      }
      const form = new FormData();
      form.set("title", title);
      form.set("category", category);
      form.set("description", description);
      form.set("email", email);
      form.set("turnstileToken", turnstileToken!);
      for (const file of files) form.append("files", file);
      return submitIssueWithFiles({ data: form });
    },
    onSuccess: () => {
      toast.success(m.issues_success());
      setTitle("");
      setDescription("");
      setEmail("");
      setFiles([]);
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

      <div>
        <label className="mb-1.5 block text-sm font-medium text-foreground/90">
          {m.issues_files_label()}
        </label>
        <input
          ref={fileInputRef}
          type="file"
          accept={ISSUE_FILE_ACCEPT}
          multiple
          className="hidden"
          data-testid="issue-files-input"
          onChange={(e) => void addFiles(e.target.files)}
        />
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={files.length >= MAX_ISSUE_FILES}
          className="flex items-center gap-2 rounded-xl border border-border bg-card/60 px-4 py-2.5 text-sm text-muted-foreground transition-colors hover:text-foreground/90 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Paperclip className="h-4 w-4" />
          {m.issues_files_hint()}
        </button>
        {files.length > 0 && (
          <ul className="mt-2 space-y-1.5">
            {files.map((file, index) => (
              <li
                key={`${file.name}-${index}`}
                className="flex items-center justify-between gap-3 rounded-lg border border-border bg-card/40 px-3 py-1.5 text-xs text-foreground"
              >
                <span className="truncate">
                  {file.name}{" "}
                  <span className="text-muted-foreground">
                    ({Math.ceil(file.size / 1024)} KB)
                  </span>
                </span>
                <button
                  type="button"
                  aria-label={m.issues_file_remove()}
                  onClick={() => setFiles(files.filter((_, i) => i !== index))}
                  className="shrink-0 text-muted-foreground transition-colors hover:text-foreground"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </li>
            ))}
          </ul>
        )}
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
              {issue.files.length > 0 && (
                <p className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px]">
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
