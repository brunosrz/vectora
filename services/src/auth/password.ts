/**
 * Hash de senha via WebCrypto PBKDF2 — nativo no runtime do Workers, sem
 * dependência externa (bcrypt/argon2 não rodam em workerd). A recomendação
 * OWASP 2023 pra PBKDF2-SHA256 é 210_000, mas o workerd (runtime real dos
 * Workers, diferente do wrangler dev local) rejeita qualquer valor acima de
 * 100_000 com `NotSupportedError` — por isso 100_000 aqui, o teto real da
 * plataforma, não escolha de segurança.
 *
 * Formato armazenado: `pbkdf2$<iterations>$<saltB64>$<hashB64>` —
 * self-describing, permite subir iterations no futuro sem invalidar hashes
 * antigos (verifyPassword lê o número gravado, não uma constante).
 */

const ITERATIONS = 100_000;
const KEY_LENGTH_BITS = 256;

function toBase64(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes));
}

function fromBase64(b64: string): Uint8Array {
  return Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
}

async function derive(
  password: string,
  salt: Uint8Array,
  iterations: number,
): Promise<Uint8Array> {
  const keyMaterial = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(password),
    "PBKDF2",
    false,
    ["deriveBits"],
  );
  const bits = await crypto.subtle.deriveBits(
    { name: "PBKDF2", salt: salt as BufferSource, iterations, hash: "SHA-256" },
    keyMaterial,
    KEY_LENGTH_BITS,
  );
  return new Uint8Array(bits);
}

export async function hashPassword(password: string): Promise<string> {
  const salt = crypto.getRandomValues(new Uint8Array(16));
  const hash = await derive(password, salt, ITERATIONS);
  return `pbkdf2$${ITERATIONS}$${toBase64(salt)}$${toBase64(hash)}`;
}

/** Comparação em tempo constante — evita timing attack no length/bytes. */
function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++)
    diff |= (a[i] as number) ^ (b[i] as number);
  return diff === 0;
}

export async function verifyPassword(
  password: string,
  stored: string,
): Promise<boolean> {
  const parts = stored.split("$");
  if (parts.length !== 4 || parts[0] !== "pbkdf2") return false;
  const [, iterationsPart, saltPart, hashPart] = parts as [
    string,
    string,
    string,
    string,
  ];
  const iterations = parseInt(iterationsPart, 10);
  if (!Number.isFinite(iterations) || iterations <= 0) return false;
  const salt = fromBase64(saltPart);
  const expected = fromBase64(hashPart);
  const actual = await derive(password, salt, iterations);
  return timingSafeEqual(actual, expected);
}
