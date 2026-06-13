import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getSubscription,
  createCheckout,
  createPortal,
  getLicenseHistory,
} from "#/server/fns/subscription";

export const SUBSCRIPTION_QUERY_KEY = ["subscription"] as const;
export const LICENSE_HISTORY_QUERY_KEY = ["license-checks"] as const;

export function useSubscription() {
  return useQuery({
    queryKey: SUBSCRIPTION_QUERY_KEY,
    queryFn: () => getSubscription(),
    staleTime: 30_000,
  });
}

export function useLicenseHistory() {
  return useQuery({
    queryKey: LICENSE_HISTORY_QUERY_KEY,
    queryFn: () => getLicenseHistory(),
    staleTime: 5 * 60_000,
  });
}

export function useCreateCheckout() {
  return useMutation({
    mutationFn: (plan: "plus" | "pro") => createCheckout({ data: { plan } }),
    onSuccess: ({ url }) => {
      window.location.href = url;
    },
  });
}

export function useCreatePortal() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => createPortal(),
    onSuccess: ({ url }) => {
      qc.invalidateQueries({ queryKey: SUBSCRIPTION_QUERY_KEY });
      window.location.href = url;
    },
  });
}
