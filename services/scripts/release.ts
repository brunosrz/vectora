/**
 * Publica os instaladores de `vectora/electron/dist-electron/` no R2 e atualiza
 * o canal de release no KV (`channels.<channel>.version`).
 *
 * Uso (depois de `scons release-<os>`, a partir de services/):
 *   pnpm release -- --channel=latest --version=0.1.1 [--dist=<path>]
 *
 * Sobe pra key `<channel>/<os>/<arch>/<version>/<filename>` (mesmo padrão que
 * `updates/worker.ts` já lê em GET /updates/... e GET /download/...). O
 * manifesto `latest*.yml` que o electron-builder gera junto vai pro mesmo
 * lugar, com o nome fixo `latest.yml` (é o que
 * `GET /updates/:channel/:os/:arch/latest.yml` espera).
 */
import { execFileSync } from "node:child_process";
import { readdirSync } from "node:fs";
import { join } from "node:path";

const CONTENT_TYPES: Record<string, string> = {
  exe: "application/x-msdownload",
  msi: "application/x-msi",
  dmg: "application/x-apple-diskimage",
  AppImage: "application/x-executable",
  deb: "application/vnd.debian.binary-package",
  rpm: "application/x-rpm",
  yml: "application/x-yaml",
  blockmap: "application/octet-stream",
};

// `Vectora-0.1.1-win-x64.exe` → { version: "0.1.1", os: "win", arch: "x64", ext: "exe" }
// Manifests (`latest.yml`, `latest-mac.yml`, `latest-linux.yml`) não seguem
// esse padrão — tratados à parte via MANIFEST_OS abaixo.
export const INSTALLER_RE =
  /^Vectora-(?<version>[^-]+)-(?<os>win|mac|linux)-(?<arch>x64|arm64|universal)\.(?<ext>exe|msi|dmg|AppImage|deb|rpm)$/;

export const MANIFEST_OS: Record<string, string> = {
  "latest.yml": "win",
  "latest-mac.yml": "mac",
  "latest-linux.yml": "linux",
};

// Arquiteturas reais publicadas por SO (electron-builder.yml). mac só builda
// arm64 (Intel descontinuado); win e linux buildam os dois numa job só.
export const MANIFEST_ARCHES: Record<string, string[]> = {
  win: ["x64", "arm64"],
  mac: ["arm64"],
  linux: ["x64", "arm64"],
};

// Quantas versões ficam disponíveis em R2 por canal. wrangler não expõe
// listagem de objetos (só get/put/delete) — em vez de descobrir versões
// antigas escaneando o bucket, o config no KV grava (via `uploads` abaixo)
// exatamente quais chaves cada versão publicou, e a poda apaga por essa
// lista. 3 dá margem pra quem já está baixando uma versão no meio de um
// up-release nunca ver o download sumir no meio do caminho.
export const RETENTION_COUNT = 3;

export function computeRetention(
  history: string[],
  newVersion: string,
  retain: number = RETENTION_COUNT,
): { retained: string[]; pruned: string[] } {
  const safeRetain = Math.max(retain, 1);
  const updated = [...history.filter((v) => v !== newVersion), newVersion];
  if (updated.length <= safeRetain) {
    return { retained: updated, pruned: [] };
  }
  return {
    retained: updated.slice(updated.length - safeRetain),
    pruned: updated.slice(0, updated.length - safeRetain),
  };
}

export function parseArgs(argv: string[]) {
  const args = Object.fromEntries(
    argv
      .filter((a) => a.startsWith("--"))
      .map((a) => a.slice(2).split("=") as [string, string]),
  );
  const channel = args.channel ?? "latest";
  const version = args.version;
  const dist =
    args.dist ??
    join(__dirname, "..", "..", "vectora", "electron", "dist-electron");
  if (!version) {
    throw new Error("--version=X.Y.Z é obrigatório");
  }
  return { channel, version, dist };
}

export function extOf(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot === -1 ? "" : filename.slice(dot + 1);
}

function uploadFile(
  bucket: string,
  key: string,
  filePath: string,
  contentType: string,
) {
  execFileSync(
    "npx",
    [
      "wrangler",
      "r2",
      "object",
      "put",
      `${bucket}/${key}`,
      "--file",
      filePath,
      "--content-type",
      contentType,
      "--remote",
    ],
    { stdio: "inherit" },
  );
}

function deleteFile(bucket: string, key: string) {
  execFileSync(
    "npx",
    ["wrangler", "r2", "object", "delete", `${bucket}/${key}`, "--remote"],
    { stdio: "inherit" },
  );
}

interface StoredConfig {
  channels: Record<
    string,
    {
      version: string;
      rollout_percent: number;
      previous_stable?: string;
      history: string[];
    }
  >;
  quarantined: string[];
  // "<channel>/<version>" → chaves R2 publicadas por essa versão, pra poda
  // apagar com precisão sem precisar listar o bucket.
  uploads: Record<string, string[]>;
}

function readConfig(): StoredConfig {
  try {
    const raw = execFileSync(
      "npx",
      ["wrangler", "kv", "key", "get", "config", "--binding=KV", "--remote"],
      { encoding: "utf-8" },
    );
    const parsed = JSON.parse(raw) as Partial<StoredConfig>;
    return {
      channels: parsed.channels ?? {},
      quarantined: parsed.quarantined ?? [],
      uploads: parsed.uploads ?? {},
    };
  } catch {
    return { channels: {}, quarantined: [], uploads: {} };
  }
}

function writeConfig(config: StoredConfig) {
  execFileSync(
    "npx",
    [
      "wrangler",
      "kv",
      "key",
      "put",
      "config",
      JSON.stringify(config),
      "--binding=KV",
      "--remote",
    ],
    { stdio: "inherit" },
  );
}

/**
 * Grava a nova versão no canal, registra as chaves R2 que ela publicou e
 * poda versões além de RETENTION_COUNT, apagando as chaves gravadas na
 * publicação delas.
 */
function publishVersionAndPrune(
  bucket: string,
  channel: string,
  version: string,
  uploadedKeys: string[],
) {
  const config = readConfig();
  const existing = config.channels[channel];
  const { retained, pruned } = computeRetention(
    existing?.history ?? [],
    version,
  );

  config.channels[channel] = {
    version,
    rollout_percent: existing?.rollout_percent ?? 100,
    ...(existing?.version ? { previous_stable: existing.version } : {}),
    history: retained,
  };
  config.uploads[`${channel}/${version}`] = uploadedKeys;

  for (const prunedVersion of pruned) {
    const prunedKey = `${channel}/${prunedVersion}`;
    for (const key of config.uploads[prunedKey] ?? []) {
      deleteFile(bucket, key);
    }
    delete config.uploads[prunedKey];
  }

  writeConfig(config);
  if (pruned.length > 0) {
    console.log(
      `✓ versões podadas do canal "${channel}": ${pruned.join(", ")}`,
    );
  }
}

function main() {
  const { channel, version, dist } = parseArgs(process.argv.slice(2));
  const bucket = "vectora-r2";

  const files = readdirSync(dist).filter(
    (f) => !f.endsWith(".yml.tmp") && !f.startsWith("."),
  );

  const uploadedKeys: string[] = [];
  for (const file of files) {
    const manifestOs = MANIFEST_OS[file];
    if (manifestOs) {
      for (const arch of MANIFEST_ARCHES[manifestOs] ?? []) {
        const key = `${channel}/${manifestOs}/${arch}/${version}/latest.yml`;
        uploadFile(bucket, key, join(dist, file), CONTENT_TYPES.yml);
        uploadedKeys.push(key);
      }
      continue;
    }

    const match = INSTALLER_RE.exec(file);
    if (!match?.groups) continue; // blockmap e outros artefatos auxiliares — não distribuídos
    const { os, arch } = match.groups;
    const key = `${channel}/${os}/${arch}/${version}/${file}`;
    const contentType =
      CONTENT_TYPES[extOf(file)] ?? "application/octet-stream";
    uploadFile(bucket, key, join(dist, file), contentType);
    uploadedKeys.push(key);
  }

  if (uploadedKeys.length === 0) {
    throw new Error(`Nenhum instalador/manifesto reconhecido em ${dist}`);
  }

  publishVersionAndPrune(bucket, channel, version, uploadedKeys);
  console.log(
    `✓ ${uploadedKeys.length} arquivo(s) publicados no canal "${channel}" v${version}`,
  );
}

if (require.main === module) {
  main();
}
