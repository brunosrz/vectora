/**
 * Teste de update REAL, contra o Worker publicado em produção — sem nenhum
 * mock (nem cloudflare:test, nem KV/R2 fake). Roda no projeto "node" do
 * vitest (mesmo pool que release.test.ts), processo Node puro com `fetch`
 * nativo, contra `https://services.vectora.company`.
 *
 * Depende de rede/produção real — não entra em `scons tests` (quebraria CI
 * hermético sempre que a rede cair ou o Worker estiver temporariamente
 * fora). Config própria (vitest.live.config.mts), fora dos `projects` do
 * config default. Rodar manualmente:
 *   pnpm --dir services exec vitest run --config vitest.live.config.mts
 *
 * Não hardcoda nenhum número de versão — descobre tudo dinamicamente
 * consultando o Worker real, então continua válido conforme novos releases
 * empurram versões antigas pra fora da janela de retenção (RETENTION_COUNT
 * = 3 em scripts/release.ts). Não assume Content-Length em nenhuma resposta
 * — o Worker serve o body do R2 em streaming, sem declarar tamanho
 * antecipado em HEAD nem suportar Range; a única forma confiável de provar
 * "existe conteúdo real" é ler ao menos um chunk do body de verdade.
 */
import { describe, it, expect } from "vitest";

const BASE_URL = "https://services.vectora.company";

/** Lê o primeiro chunk do body sem baixar o resto — prova que existe
 * conteúdo real por trás da URL sem trazer um binário de centenas de MB
 * pra memória do teste. */
async function firstChunkNonEmpty(res: Response): Promise<boolean> {
  const reader = res.body?.getReader();
  if (!reader) return false;
  try {
    const { value, done } = await reader.read();
    return !done && !!value && value.byteLength > 0;
  } finally {
    await reader.cancel().catch(() => {});
  }
}

describe("live update — contra o Worker real de produção", () => {
  it("GET /version/latest devolve a versão estável publicada agora", async () => {
    const res = await fetch(`${BASE_URL}/version/latest`);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { version: string; channel: string };
    expect(body.channel).toBe("latest");
    expect(body.version).toMatch(/^\d+\.\d+\.\d+$/);
  });

  it(
    "manifestos de win-x64 e win-arm64 nunca se misturam — prova viva da " +
      "regressão corrigida na PR #48 (getExactArchObject)",
    async () => {
      const [resX64, resArm64] = await Promise.all([
        fetch(`${BASE_URL}/updates/latest/win/x64/latest.yml`),
        fetch(`${BASE_URL}/updates/latest/win/arm64/latest.yml`),
      ]);
      expect(resX64.status).toBe(200);
      expect(resArm64.status).toBe(200);

      const [yamlX64, yamlArm64] = await Promise.all([
        resX64.text(),
        resArm64.text(),
      ]);

      // Parse mínimo, sem depender de um parser YAML — o campo `path:` do
      // manifesto do electron-updater é sempre uma linha "path: <filename>"
      // de topo.
      const pathOf = (yaml: string): string => {
        const m = /^path:\s*(\S+)/m.exec(yaml);
        expect(m).not.toBeNull();
        return m![1]!;
      };
      const filenameX64 = pathOf(yamlX64);
      const filenameArm64 = pathOf(yamlArm64);

      // A asserção real deste teste: os dois manifestos nunca podem apontar
      // pro MESMO arquivo — cada um lista o instalador da própria arch.
      expect(filenameX64).not.toBe(filenameArm64);
      expect(filenameX64).toContain("-win-x64.");
      expect(filenameArm64).toContain("-win-arm64.");
    },
  );

  it("binário real listado no manifesto de win-x64 existe e tem conteúdo", async () => {
    const manifestRes = await fetch(
      `${BASE_URL}/updates/latest/win/x64/latest.yml`,
    );
    expect(manifestRes.status).toBe(200);
    const version = manifestRes.headers.get("x-vectora-version");
    expect(version).toMatch(/^\d+\.\d+\.\d+$/);

    const yaml = await manifestRes.text();
    const pathMatch = /^path:\s*(\S+)/m.exec(yaml);
    expect(pathMatch).not.toBeNull();
    const filename = pathMatch![1]!;

    const downloadUrl = `${BASE_URL}/updates/latest/win/x64/${version}/${filename}`;
    const downloadRes = await fetch(downloadUrl);
    expect(downloadRes.status).toBe(200);
    expect(await firstChunkNonEmpty(downloadRes)).toBe(true);
  });

  it("GET /download/latest/win-x64.exe (primeira instalação, sem token) resolve pra um binário real", async () => {
    const res = await fetch(`${BASE_URL}/download/latest/win-x64.exe`);
    expect(res.status).toBe(200);
    expect(res.headers.get("x-vectora-version")).toMatch(/^\d+\.\d+\.\d+$/);
    expect(await firstChunkNonEmpty(res)).toBe(true);
  });
});
