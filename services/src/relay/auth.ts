import type { JwtPayload } from "./types";

const BASE36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz";
const TOKEN_LENGTH = 6;

export async function verifyJwt(
  token: string,
  secret: string,
): Promise<JwtPayload> {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("invalid JWT format");

  const [headerB64, payloadB64, sigB64] = parts as [string, string, string];

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["verify"],
  );

  const sigBytes = Uint8Array.from(
    atob(sigB64.replace(/-/g, "+").replace(/_/g, "/")),
    (c) => c.charCodeAt(0),
  );

  const valid = await crypto.subtle.verify(
    "HMAC",
    key,
    sigBytes,
    new TextEncoder().encode(`${headerB64}.${payloadB64}`),
  );
  if (!valid) throw new Error("invalid JWT signature");

  let payload: JwtPayload;
  try {
    payload = JSON.parse(
      atob(payloadB64.replace(/-/g, "+").replace(/_/g, "/")),
    ) as JwtPayload;
  } catch {
    throw new Error("invalid JWT payload");
  }

  if (!payload.sub) throw new Error("JWT missing sub claim");
  if (payload.exp < Math.floor(Date.now() / 1000))
    throw new Error("JWT expired");

  return payload;
}

export async function generateRelayToken(
  userId: string,
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

  const data = new TextEncoder().encode(`${userId}:${fingerprint}`);
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
