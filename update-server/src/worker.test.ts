import { describe, it, expect } from "vitest";
import { rolloutBucket, resolveVersion } from "./worker";

describe("rolloutBucket", () => {
  it("é determinístico — mesmo token, mesmo bucket", () => {
    expect(rolloutBucket("client-abc")).toBe(rolloutBucket("client-abc"));
  });

  it("sempre no intervalo [0,99], inclusive vazio/unicode", () => {
    for (const t of ["a", "bbbb", "token-123", "", "🚀-cliente"]) {
      const b = rolloutBucket(t);
      expect(b).toBeGreaterThanOrEqual(0);
      expect(b).toBeLessThan(100);
    }
  });

  it("distribui — tokens diferentes não caem todos no mesmo bucket", () => {
    const buckets = new Set(
      ["a", "b", "c", "d", "e", "f", "g", "h"].map(rolloutBucket),
    );
    expect(buckets.size).toBeGreaterThan(1);
  });
});

describe("resolveVersion", () => {
  const base = {
    channels: {
      latest: {
        version: "1.2.0",
        rollout_percent: 100,
        previous_stable: "1.1.0",
      },
    },
    quarantined: [] as string[],
  };

  it("canal desconhecido → null", () => {
    expect(resolveVersion(base, "beta", "tok")).toBeNull();
  });

  it("rollout 100% → serve a versão nova", () => {
    expect(resolveVersion(base, "latest", "tok")).toBe("1.2.0");
  });

  it("rollout 0% → serve o previous_stable", () => {
    const cfg = {
      ...base,
      channels: {
        latest: { ...base.channels.latest, rollout_percent: 0 },
      },
    };
    expect(resolveVersion(cfg, "latest", "tok")).toBe("1.1.0");
  });

  it("versão quarentinada → rollback para previous_stable", () => {
    const cfg = { ...base, quarantined: ["1.2.0"] };
    expect(resolveVersion(cfg, "latest", "tok")).toBe("1.1.0");
  });

  it("quarentinada sem previous_stable → null (edge)", () => {
    const cfg = {
      channels: { latest: { version: "1.2.0", rollout_percent: 100 } },
      quarantined: ["1.2.0"],
    };
    expect(resolveVersion(cfg, "latest", "tok")).toBeNull();
  });
});
