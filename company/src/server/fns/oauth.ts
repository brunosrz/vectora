import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";
import { servicesFetch } from "#/lib/services/client";

export const authorizeDevice = createServerFn({ method: "POST" })
  .validator(z.object({ state: z.string().min(1) }))
  .handler(async ({ data: input }) => {
    return servicesFetch<{ ok: true }>("/oauth/device", {
      method: "POST",
      body: JSON.stringify(input),
    });
  });
