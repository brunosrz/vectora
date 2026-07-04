import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { servicesFetch } from "#/lib/services/client";

const IssueSchema = z.object({
  title: z.string().min(3).max(200),
  category: z.enum(["bug", "feedback", "feature"]),
  description: z.string().max(5000).optional(),
  email: z.string().email().optional().or(z.literal("")),
  turnstileToken: z.string(),
});

export const submitIssue = createServerFn({ method: "POST" })
  .validator(IssueSchema)
  .handler(async ({ data: input }) => {
    return servicesFetch<{ ok: true }>("/issues", {
      method: "POST",
      body: JSON.stringify(input),
    });
  });

const ISSUE_CATEGORIES = ["bug", "feedback", "feature"] as const;
type IssueCategory = (typeof ISSUE_CATEGORIES)[number];

export type IssueListItem = {
  id: string;
  title: string;
  category: IssueCategory;
  description: string | null;
  created_at: string;
};

export const listOpenIssues = createServerFn({ method: "GET" }).handler(
  async (): Promise<IssueListItem[]> => {
    return servicesFetch<IssueListItem[]>("/issues");
  },
);

export const joinWaitlist = createServerFn({ method: "POST" })
  .validator(
    z.object({
      email: z.string().email(),
      turnstileToken: z.string(),
      source: z.string().optional(),
    }),
  )
  .handler(async ({ data: input }) => {
    return servicesFetch<{ ok: true }>("/issues/waitlist", {
      method: "POST",
      body: JSON.stringify(input),
    });
  });
