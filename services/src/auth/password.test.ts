import { describe, expect, it } from "vitest";
import { hashPassword, verifyPassword } from "./password";

describe("hashPassword/verifyPassword", () => {
  it("hashes in the self-describing pbkdf2$iter$salt$hash format and verifies the same password", async () => {
    const hash = await hashPassword("correct horse battery staple");
    expect(hash).toMatch(/^pbkdf2\$210000\$[A-Za-z0-9+/=]+\$[A-Za-z0-9+/=]+$/);
    expect(await verifyPassword("correct horse battery staple", hash)).toBe(
      true,
    );
  });

  it("rejects a wrong password, a malformed hash, and an unsupported algorithm tag", async () => {
    const hash = await hashPassword("correct horse battery staple");
    expect(await verifyPassword("wrong password", hash)).toBe(false);
    expect(
      await verifyPassword("correct horse battery staple", "not-a-real-hash"),
    ).toBe(false);
    expect(
      await verifyPassword(
        "correct horse battery staple",
        "bcrypt$10$salt$hash",
      ),
    ).toBe(false);
  });

  it("produces different hashes (different salts) for the same password", async () => {
    const a = await hashPassword("same-password");
    const b = await hashPassword("same-password");
    expect(a).not.toBe(b);
  });
});
