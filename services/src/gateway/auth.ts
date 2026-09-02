const BASE36_CHARS = "0123456789abcdefghijklmnopqrstuvwxyz";
// 10 chars base36 ≈ 51.7 bits — no esquema antigo (6 chars, só 4 bytes do
// HMAC) o valor de 32 bits ia até ~4.29bi mas 36^6 ≈ 2.18bi, então o
// `.slice` do final descartava dígito(s) mais significativo(s) sempre que
// o valor excedia esse teto — silenciosamente colidindo fingerprints
// diferentes no mesmo token em mais de 46% dos casos. Aqui: BigInt sobre o
// digest inteiro (256 bits) reduzido por módulo ANTES de codificar — sem
// truncamento de dígito, e com margem suficiente pra qualquer volume
// realista de instalações (birthday bound despresível até dezenas de
// milhões de tokens).
const TOKEN_LENGTH = 10;
const TOKEN_SPACE = 36n ** BigInt(TOKEN_LENGTH);

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

function bytesToBigInt(bytes: Uint8Array): bigint {
  let n = 0n;
  for (const b of bytes) n = (n << 8n) | BigInt(b);
  return n;
}

/** Token público (subdomínio) — determinístico por fingerprint, mas NUNCA é
 * o único fator de autenticação (ver `generateConnectorSecret`): identifica
 * a sessão, não autoriza sozinho quem pode assumi-la. */
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
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(fingerprint),
  );
  const n = bytesToBigInt(new Uint8Array(sig)) % TOKEN_SPACE;

  let result = "";
  let rest = n;
  do {
    result = BASE36_CHARS[Number(rest % 36n)] + result;
    rest /= 36n;
  } while (rest > 0n);

  return result.padStart(TOKEN_LENGTH, "0");
}

/** Segredo de conector — 32 bytes aleatórios (256 bits), devolvido em texto
 * puro só na resposta de `/register`, nunca mais recuperável depois disso
 * (só o hash fica guardado, ver `hashConnectorSecret`). É o ÚNICO fator que
 * autoriza abrir o WebSocket como dono de uma sessão — o token público
 * (subdomínio) sozinho não basta mais, ao contrário do esquema anterior. */
export function generateConnectorSecret(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  let binary = "";
  for (const b of bytes) binary += String.fromCharCode(b);
  return btoa(binary)
    .replaceAll("+", "-")
    .replaceAll("/", "_")
    .replaceAll("=", "");
}

export async function hashConnectorSecret(secret: string): Promise<string> {
  const buf = await crypto.subtle.digest(
    "SHA-256",
    new TextEncoder().encode(secret),
  );
  return Array.from(new Uint8Array(buf))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
