import { createServerFn } from "@tanstack/react-start";
import { clearSessionCookie, servicesFetch } from "#/lib/services/client";

export const exportData = createServerFn({ method: "POST" }).handler(
  async () => {
    return servicesFetch<{ url: string }>("/gdpr/export", { method: "POST" });
  },
);

export const requestAccountDeletion = createServerFn({
  method: "POST",
}).handler(async () => {
  const res = await servicesFetch<{ ok: true }>("/gdpr/delete", {
    method: "POST",
  });
  clearSessionCookie();
  return res;
});
