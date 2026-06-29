import { createFileRoute, redirect } from "@tanstack/react-router";
import { z } from "zod";
import { exchangeOAuthCode } from "#/server/fns/auth";

const SearchSchema = z.object({
  code: z.string().optional(),
  error: z.string().optional(),
  error_description: z.string().optional(),
});

export const Route = createFileRoute("/auth/callback")({
  validateSearch: SearchSchema,
  loaderDeps: ({ search }) => ({
    code: search.code,
    error: search.error,
  }),
  loader: async ({ deps }) => {
    if (deps.error || !deps.code) {
      throw redirect({ to: "/login" });
    }
    await exchangeOAuthCode({ data: { code: deps.code } });
    throw redirect({ to: "/dashboard" });
  },
  component: () => null,
});
