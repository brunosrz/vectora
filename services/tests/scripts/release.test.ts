import { describe, it, expect } from "vitest";
import {
  parseArgs,
  extOf,
  INSTALLER_RE,
  MANIFEST_OS,
  MANIFEST_ARCHES,
  RETENTION_COUNT,
  computeRetention,
} from "../../scripts/release";

describe("parseArgs", () => {
  it("channel default é 'latest'", () => {
    const { channel } = parseArgs(["--version=0.1.1"]);
    expect(channel).toBe("latest");
  });

  it("lê version e channel explícitos", () => {
    const { channel, version } = parseArgs([
      "--channel=beta",
      "--version=0.2.0",
    ]);
    expect(channel).toBe("beta");
    expect(version).toBe("0.2.0");
  });

  it("--dist sobrescreve o default", () => {
    const { dist } = parseArgs(["--version=0.1.1", "--dist=/tmp/builds"]);
    expect(dist).toBe("/tmp/builds");
  });

  it("sem --version → lança erro (par de erro)", () => {
    expect(() => parseArgs([])).toThrow("--version=X.Y.Z é obrigatório");
  });
});

describe("extOf", () => {
  it("extrai a extensão", () => {
    expect(extOf("Vectora-0.1.0-win-x64.exe")).toBe("exe");
    expect(extOf("latest.yml")).toBe("yml");
  });

  it("sem extensão → string vazia (edge)", () => {
    expect(extOf("semextensao")).toBe("");
  });
});

describe("INSTALLER_RE", () => {
  it("reconhece o padrão real do electron-builder", () => {
    const match = INSTALLER_RE.exec("Vectora-0.1.0-win-x64.exe");
    expect(match?.groups).toEqual({
      version: "0.1.0",
      os: "win",
      arch: "x64",
      ext: "exe",
    });
  });

  it("não reconhece blockmap nem arquivos fora do padrão (par de erro)", () => {
    expect(INSTALLER_RE.exec("Vectora-0.1.0-win-x64.exe.blockmap")).toBeNull();
    expect(INSTALLER_RE.exec("random-file.txt")).toBeNull();
    expect(INSTALLER_RE.exec("latest.yml")).toBeNull();
  });

  it("aceita mac universal e linux arm64", () => {
    expect(
      INSTALLER_RE.exec("Vectora-1.0.0-mac-universal.dmg")?.groups?.arch,
    ).toBe("universal");
    expect(
      INSTALLER_RE.exec("Vectora-1.0.0-linux-arm64.AppImage")?.groups?.os,
    ).toBe("linux");
  });
});

describe("MANIFEST_OS", () => {
  it("mapeia os 3 nomes de manifesto do electron-builder", () => {
    expect(MANIFEST_OS["latest.yml"]).toBe("win");
    expect(MANIFEST_OS["latest-mac.yml"]).toBe("mac");
    expect(MANIFEST_OS["latest-linux.yml"]).toBe("linux");
  });
});

describe("MANIFEST_ARCHES", () => {
  it("win e linux publicam manifesto em x64 e arm64", () => {
    expect(MANIFEST_ARCHES.win).toEqual(["x64", "arm64"]);
    expect(MANIFEST_ARCHES.linux).toEqual(["x64", "arm64"]);
  });

  it("mac só publica manifesto em arm64 (Intel descontinuado, par de erro)", () => {
    expect(MANIFEST_ARCHES.mac).toEqual(["arm64"]);
    expect(MANIFEST_ARCHES.mac).not.toContain("x64");
  });
});

describe("computeRetention", () => {
  it("histórico vazio: primeira publicação vira o único item retido", () => {
    const { retained, pruned } = computeRetention([], "0.1.0");
    expect(retained).toEqual(["0.1.0"]);
    expect(pruned).toEqual([]);
  });

  it("abaixo do limite: nada é podado", () => {
    const { retained, pruned } = computeRetention(["0.1.0", "0.1.1"], "0.1.2");
    expect(retained).toEqual(["0.1.0", "0.1.1", "0.1.2"]);
    expect(pruned).toEqual([]);
  });

  it("exatamente no limite (RETENTION_COUNT=3): nada é podado", () => {
    const { retained, pruned } = computeRetention(
      ["0.1.0", "0.1.1"],
      "0.1.2",
      3,
    );
    expect(retained).toHaveLength(3);
    expect(pruned).toEqual([]);
  });

  it("um acima do limite: poda só a mais antiga (par de erro)", () => {
    const { retained, pruned } = computeRetention(
      ["0.1.0", "0.1.1", "0.1.2"],
      "0.1.3",
      3,
    );
    expect(retained).toEqual(["0.1.1", "0.1.2", "0.1.3"]);
    expect(pruned).toEqual(["0.1.0"]);
  });

  it("republicar a mesma versão não duplica nem poda a si mesma", () => {
    const { retained, pruned } = computeRetention(
      ["0.1.0", "0.1.1", "0.1.2"],
      "0.1.2",
      3,
    );
    expect(retained).toEqual(["0.1.0", "0.1.1", "0.1.2"]);
    expect(pruned).toEqual([]);
  });

  it("retain=0 ou negativo (edge): nunca poda a versão recém-publicada", () => {
    const { retained, pruned } = computeRetention(["0.1.0"], "0.1.1", 0);
    expect(retained).toEqual(["0.1.1"]);
    expect(pruned).toEqual(["0.1.0"]);
  });

  it("RETENTION_COUNT default é 3", () => {
    expect(RETENTION_COUNT).toBe(3);
  });
});
