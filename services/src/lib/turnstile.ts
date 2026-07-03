/**
 * Cloudflare Turnstile — mesma verificação que a company fazia
 * (src/lib/turnstile.ts), portada pra cá porque signup/login/issues/waitlist
 * agora nascem em services. Sem TURNSTILE_SECRET_KEY (wrangler dev local sem
 * secret configurado) dispensa a checagem — em produção o secret é sempre
 * setado, então isso nunca bypassa de verdade fora de dev.
 */
export interface TurnstileResult {
  success: boolean;
  errorCodes?: string[];
}

export async function verifyTurnstile(
  token: string,
  secretKey: string | undefined,
  ip?: string,
): Promise<TurnstileResult> {
  if (!secretKey) return { success: true };

  const body: Record<string, string> = { secret: secretKey, response: token };
  if (ip) body.remoteip = ip;

  const res = await fetch(
    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );

  const data = (await res.json()) as {
    success: boolean;
    "error-codes"?: string[];
  };

  return { success: data.success, errorCodes: data["error-codes"] };
}
