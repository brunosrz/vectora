import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { m } from "#/paraglide/messages";
import Turnstile from "#/components/shared/Turnstile";
import { submitIssue } from "#/server/fns/issues";
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
        <label className="mb-1.5 block text-sm font-medium text-slate-300">
          {m.issues_title_label()}
        </label>
        <input
          type="text"
          required
          minLength={3}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-xl border border-brand-700 bg-brand-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-300">
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
                  ? "border-brand-500 bg-brand-500/10 text-brand-300"
                  : "border-brand-700 text-slate-500 hover:text-slate-300"
              }`}
            >
              {CATEGORY_LABELS[c]}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-300">
          {m.issues_desc_label()}
        </label>
        <textarea
          required
          minLength={10}
          rows={5}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="w-full resize-none rounded-xl border border-brand-700 bg-brand-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors"
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-slate-300">
          {m.issues_email_label()}
        </label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="opcional — para receber atualizações"
          className="w-full rounded-xl border border-brand-700 bg-brand-800/60 px-4 py-2.5 text-sm text-white placeholder:text-slate-500 outline-none focus:border-brand-500 transition-colors"
        />
      </div>

      <Turnstile onSuccess={setTurnstileToken} />

      <button
        type="submit"
        disabled={!canSubmit}
        className="rounded-xl bg-brand-500 px-6 py-2.5 text-sm font-semibold text-white shadow shadow-brand-500/25 transition-all hover:bg-brand-400 disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {mutation.isPending ? m.form_submitting() : m.issues_submit()}
      </button>
    </form>
  );
}

function IssuesPage() {
  return (
    <div className="mx-auto max-w-xl px-4 py-16 sm:px-6">
      <div className="mb-10">
        <h1 className="mb-2 text-3xl font-semibold text-white">
          {m.page_issues_title()}
        </h1>
        <p className="text-slate-400">{m.issues_subtitle()}</p>
      </div>
      <IssueForm />
    </div>
  );
}
