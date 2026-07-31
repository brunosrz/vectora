"use client";

import { useEffect, useState } from "react";

interface FeatureFlags {
  enableFeaturesBeta: boolean;
  /** 3º modo de interface (Kanban), dev-only via `VECTORA_DEV=1`. */
  enableKanbanMode: boolean;
}

// Default desligado: se o fetch falhar, a feature dev-only não aparece pro
// usuário comum — falha fechada.
const DEFAULT_FLAGS: FeatureFlags = {
  enableFeaturesBeta: false,
  enableKanbanMode: false,
};

let flagsCache: FeatureFlags | null = null;
let flagsRequest: Promise<FeatureFlags> | null = null;

async function loadFlags(): Promise<FeatureFlags> {
  if (flagsCache) return flagsCache;
  if (flagsRequest) return flagsRequest;
  flagsRequest = fetch("/settings/flags")
    .then((r) =>
      r.ok
        ? (r.json() as Promise<{
            enable_features_beta: boolean;
            enable_kanban_mode?: boolean;
          }>)
        : Promise.reject(),
    )
    .then((data) => {
      flagsCache = {
        enableFeaturesBeta: data.enable_features_beta,
        enableKanbanMode: data.enable_kanban_mode ?? false,
      };
      return flagsCache;
    })
    .catch(() => {
      flagsCache = DEFAULT_FLAGS;
      return DEFAULT_FLAGS;
    });
  return flagsRequest;
}

export function useFeatureFlags(): FeatureFlags {
  const [flags, setFlags] = useState<FeatureFlags>(flagsCache ?? DEFAULT_FLAGS);

  useEffect(() => {
    void loadFlags().then(setFlags);
  }, []);

  return flags;
}
