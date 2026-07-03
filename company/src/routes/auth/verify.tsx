import { createFileRoute, redirect } from "@tanstack/react-router";
import { z } from "zod";
import { verifyEmail } from "#/server/fns/auth";

const SearchSchema = z.object({ token: z.string().optional() });

export const Route = createFileRoute("/auth/verify")({
  validateSearch: SearchSchema,
  loaderDeps: ({ search }) => ({ token: search.token }),
  loader: async ({ deps }) => {
    if (!deps.token) {
      throw redirect({ to: "/login" });
    }
    const res = await verifyEmail({ data: { token: deps.token } });
    throw redirect({ to: res.redirect as "/dashboard" });
  },
  component: () => null,
});
