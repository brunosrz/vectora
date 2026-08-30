/** Criptografia da chave de provider do Vectora Bot for GHA (AES-GCM).
 *
 * Cloudflare Secrets Store não serve pra isso: cada secret exige um
 * binding ESTÁTICO declarado no wrangler.jsonc no deploy — não dá pra ler
 * um valor dinâmico por nome em runtime, só o que já foi pré-declarado. A
 * API de Secrets Store também não expõe leitura de valor, só criar/
 * atualizar/apagar. Um Worker multi-tenant (N usuários, cada um com sua
 * própria chave de provider) não cabe nesse modelo.
 *
 * Aqui: 1 secret só (GHA_BOT_ENCRYPTION_KEY, binding estático comum),
 * usado como chave mestra AES-256-GCM pra cifrar/decifrar a chave de cada
 * usuário antes de gravar/ler de `gha_bot_config.provider_api_key_encrypted`.
 */

const IV_BYTES = 12; // recomendado pelo NIST para AES-GCM

async function importMasterKey(base64Key: string): Promise<CryptoKey> {
  const raw = Uint8Array.from(atob(base64Key), (c) => c.charCodeAt(0));
  return crypto.subtle.importKey("raw", raw, { name: "AES-GCM" }, false, [
    "encrypt",
    "decrypt",
  ]);
}

function toBase64(bytes: Uint8Array): string {
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary);
}

function fromBase64(b64: string): Uint8Array {
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
}

/** Cifra `plaintext` com a chave mestra. Retorna `base64(iv) + "." + base64(ciphertext)`. */
export async function encryptProviderKey(
  masterKeyBase64: string,
  plaintext: string,
): Promise<string> {
  const key = await importMasterKey(masterKeyBase64);
  const iv = crypto.getRandomValues(new Uint8Array(IV_BYTES));
  const ciphertext = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv },
    key,
    new TextEncoder().encode(plaintext),
  );
  return `${toBase64(iv)}.${toBase64(new Uint8Array(ciphertext))}`;
}

/** Decifra o valor produzido por `encryptProviderKey`. */
export async function decryptProviderKey(
  masterKeyBase64: string,
  encoded: string,
): Promise<string> {
  const [ivB64, ciphertextB64] = encoded.split(".");
  if (!ivB64 || !ciphertextB64) {
    throw new Error("provider_api_key_encrypted malformado");
  }
  const key = await importMasterKey(masterKeyBase64);
  const plaintext = await crypto.subtle.decrypt(
    { name: "AES-GCM", iv: fromBase64(ivB64) },
    key,
    fromBase64(ciphertextB64),
  );
  return new TextDecoder().decode(plaintext);
}
