import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { servicesFetch } from "#/lib/services/client";

export interface ApiKey {
  id: string;
  name: string;
  scopes: string[];
  created_at: string;
  last_used_at: string | null;
}

export const listApiKeys = createServerFn({ method: "GET" }).handler(
  async () => {
    return servicesFetch<ApiKey[]>("/api-keys");
  },
);

export const createApiKey = createServerFn({ method: "POST" })
  .validator(
    z.object({
      name: z.string().min(1).max(64),
      scopes: z.array(z.enum(["read", "write", "admin"])),
    }),
  )
  .handler(async ({ data: input }) => {
    return servicesFetch<{ secret: string }>("/api-keys", {
      method: "POST",
      body: JSON.stringify(input),
    });
  });

export const revokeApiKey = createServerFn({ method: "POST" })
  .validator(z.object({ id: z.string().uuid() }))
  .handler(async ({ data: input }) => {
    return servicesFetch<{ ok: true }>(`/api-keys/${input.id}/revoke`, {
      method: "POST",
    });
  });
