const BASE36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz";
const TOKEN_LENGTH = 6;

/** Compara duas strings em tempo constante — evita timing attack no secret fixo do app. */
export function timingSafeEqual(a: string, b: string): boolean {
  const encoder = new TextEncoder();
  const aBytes = encoder.encode(a);
  const bBytes = encoder.encode(b);
  if (aBytes.length !== bBytes.length) return false;
  let diff = 0;
  for (let i = 0; i < aBytes.length; i++) {
    diff |= (aBytes[i] ?? 0) ^ (bBytes[i] ?? 0);
  }
  return diff === 0;
}

export async function generateGatewayToken(
  fingerprint: string,
  secret: string,
): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );

  const data = new TextEncoder().encode(fingerprint);
  const sig = await crypto.subtle.sign("HMAC", key, data);
  const bytes = new Uint8Array(sig);

  // 4 bytes → 32-bit unsigned int → base36 → pad to TOKEN_LENGTH
  const num =
    ((bytes[0] ?? 0) << 24) |
    ((bytes[1] ?? 0) << 16) |
    ((bytes[2] ?? 0) << 8) |
    (bytes[3] ?? 0);
  const unsigned = num >>> 0;

  let result = "";
  let n = unsigned;
  do {
    result = (BASE36_CHARS[n % 36] ?? "0") + result;
    n = Math.floor(n / 36);
  } while (n > 0);

  return result.padStart(TOKEN_LENGTH, "0").slice(-TOKEN_LENGTH);
}
