import { useQuery } from "@tanstack/react-query";

// Mesmo worker que resolve o download de "latest" (services/src/updates/worker.ts)
// — o número de versão exibido no site nunca é hardcoded, vem do mesmo canal
// que decide qual binário `/download/latest/...` de fato serve.
const UPDATE_SERVER = "https://services.vectora.company";

export const LATEST_VERSION_QUERY_KEY = ["latest-version"] as const;

interface VersionResponse {
  version: string;
  channel: string;
}

async function fetchLatestVersion(channel: string): Promise<string | null> {
  const res = await fetch(`${UPDATE_SERVER}/version/${channel}`);
  if (!res.ok) return null;
  const data = (await res.json()) as VersionResponse;
  return data.version;
}

/** Versão atual do canal "latest" — null se a API estiver fora do ar ou sem
 * versão publicada ainda; nunca lança (degrada escondendo o badge). */
export function useLatestVersion(channel = "latest") {
  return useQuery({
    queryKey: [...LATEST_VERSION_QUERY_KEY, channel],
    queryFn: () => fetchLatestVersion(channel),
    staleTime: 5 * 60_000,
    retry: 1,
  });
}
