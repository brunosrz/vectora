import { createServerFn } from "@tanstack/react-start";
import { servicesFetch } from "#/lib/services/client";

export const getTokenStatus = createServerFn({ method: "GET" }).handler(
  async () => {
    return servicesFetch<{ available: boolean }>("/license/token-status");
  },
);

export const getToken = createServerFn({ method: "POST" }).handler(async () => {
  return servicesFetch<{ token: string }>("/license/token/reveal", {
    method: "POST",
  });
});

export const rotateToken = createServerFn({ method: "POST" }).handler(
  async () => {
    return servicesFetch<{ token: string }>("/license/rotate", {
      method: "POST",
    });
  },
);
