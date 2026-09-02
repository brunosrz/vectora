import { describe, it, expect } from "vitest";
import {
  encryptProviderKey,
  decryptProviderKey,
} from "../../src/gha-bot/crypto";

// Mesma chave fixa de 32 bytes usada em vitest.config.mts (GHA_BOT_ENCRYPTION_KEY)
// — não usada em produção, só pra ter uma AES-256-GCM válida e estável aqui.
const MASTER_KEY = "BwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwcHBwc=";

describe("encryptProviderKey / decryptProviderKey", () => {
  it("round-trip: decifra exatamente o plaintext original", async () => {
    const encrypted = await encryptProviderKey(
      MASTER_KEY,
      "sk-ant-minha-chave-secreta",
    );
    const decrypted = await decryptProviderKey(MASTER_KEY, encrypted);
    expect(decrypted).toBe("sk-ant-minha-chave-secreta");
  });

  it("mesmo plaintext cifrado duas vezes produz saídas diferentes (IV aleatório)", async () => {
    const a = await encryptProviderKey(MASTER_KEY, "mesma-chave");
    const b = await encryptProviderKey(MASTER_KEY, "mesma-chave");
    expect(a).not.toBe(b);
  });

  it("formato de saída é base64(iv).base64(ciphertext)", async () => {
    const encrypted = await encryptProviderKey(MASTER_KEY, "x");
    const parts = encrypted.split(".");
    expect(parts).toHaveLength(2);
    expect(() => atob(parts[0]!)).not.toThrow();
    expect(() => atob(parts[1]!)).not.toThrow();
  });

  it("erro de borda — valor sem separador '.' levanta erro tipado", async () => {
    await expect(
      decryptProviderKey(MASTER_KEY, "sem-ponto-nenhum"),
    ).rejects.toThrow("provider_api_key_encrypted malformado");
  });

  it("erro de borda — valor com iv ou ciphertext vazio levanta erro tipado", async () => {
    await expect(decryptProviderKey(MASTER_KEY, ".semiv")).rejects.toThrow(
      "provider_api_key_encrypted malformado",
    );
    await expect(
      decryptProviderKey(MASTER_KEY, "semciphertext."),
    ).rejects.toThrow("provider_api_key_encrypted malformado");
  });

  it("erro de borda — ciphertext corrompido falha a verificação de integridade do GCM", async () => {
    const encrypted = await encryptProviderKey(MASTER_KEY, "chave-original");
    const [iv, ciphertext] = encrypted.split(".");
    // Inverte a ordem dos bytes do ciphertext — corrompe sem mudar o tamanho.
    const corrupted = `${iv}.${ciphertext!.split("").reverse().join("")}`;
    await expect(decryptProviderKey(MASTER_KEY, corrupted)).rejects.toThrow();
  });

  it("erro de borda — chave mestra errada não decifra o valor de outra chave", async () => {
    const otherKey = btoa(String.fromCharCode(...new Uint8Array(32).fill(1)));
    const encrypted = await encryptProviderKey(MASTER_KEY, "chave-original");
    await expect(decryptProviderKey(otherKey, encrypted)).rejects.toThrow();
  });
});
