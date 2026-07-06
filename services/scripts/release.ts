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

function putChannelVersion(channel: string, version: string) {
  // Lê o config atual (se existir) pra preservar rollout_percent e mover a
  // versão anterior pra previous_stable — publicar não deve apagar histórico
  // de rollback.
  let current: {
    channels: Record<
      string,
      { version: string; rollout_percent: number; previous_stable?: string }
    >;
    quarantined: string[];
  };
  try {
    const raw = execFileSync(
      "npx",
      ["wrangler", "kv", "key", "get", "config", "--binding=KV", "--remote"],
      { encoding: "utf-8" },
    );
    current = JSON.parse(raw);
  } catch {
    current = { channels: {}, quarantined: [] };
  }

  const previous = current.channels[channel]?.version;
  current.channels[channel] = {
    version,
    rollout_percent: current.channels[channel]?.rollout_percent ?? 100,
    ...(previous ? { previous_stable: previous } : {}),
  };

  execFileSync(
    "npx",
    [
      "wrangler",
      "kv",
      "key",
      "put",
      "config",
      JSON.stringify(current),
      "--binding=KV",
      "--remote",
    ],
    { stdio: "inherit" },
  );
}

function main() {
  const { channel, version, dist } = parseArgs(process.argv.slice(2));
  const bucket = "vectora-r2";

  const files = readdirSync(dist).filter(
    (f) => !f.endsWith(".yml.tmp") && !f.startsWith("."),
  );

  let uploaded = 0;
  for (const file of files) {
    const manifestOs = MANIFEST_OS[file];
    if (manifestOs) {
      for (const arch of ["x64", "arm64"]) {
        const key = `${channel}/${manifestOs}/${arch}/${version}/latest.yml`;
        uploadFile(bucket, key, join(dist, file), CONTENT_TYPES.yml);
        uploaded++;
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
    uploaded++;
  }

  if (uploaded === 0) {
    throw new Error(`Nenhum instalador/manifesto reconhecido em ${dist}`);
  }

  putChannelVersion(channel, version);
  console.log(
    `✓ ${uploaded} arquivo(s) publicados no canal "${channel}" v${version}`,
  );
}

if (require.main === module) {
  main();
}
