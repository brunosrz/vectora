import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { servicesFetch } from "#/lib/services/client";

export const updateProfile = createServerFn({ method: "POST" })
  .validator(
    z.object({
      full_name: z.string().min(2).max(100).optional(),
      country: z.enum(["BR", "INTL"]).optional(),
      language: z.string().min(2).max(10).optional(),
    }),
  )
  .handler(async ({ data: input }) => {
    return servicesFetch<{ ok: true }>("/profile/update", {
      method: "POST",
      body: JSON.stringify(input),
    });
  });
