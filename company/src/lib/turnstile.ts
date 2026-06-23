// Cloudflare Turnstile — proteção bot sem fricção para o usuário
// https://developers.cloudflare.com/turnstile/
//
// Uso no cliente: renderizar <div class="cf-turnstile" data-sitekey={TURNSTILE_SITE_KEY} />
// Ou via React component (src/components/shared/Turnstile.tsx quando implementado)
//
// Verificação no servidor: chamar verifyTurnstile() dentro de createServerFn()

export const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY as
  | string
  | undefined;

export interface TurnstileVerifyResult {
  success: boolean;
  errorCodes?: string[];
}

export async function verifyTurnstile(
  token: string,
  ip?: string,
): Promise<TurnstileVerifyResult> {
  const body: Record<string, string> = {
    secret: process.env.TURNSTILE_SECRET_KEY!,
    response: token,
  };
  if (ip) body["remoteip"] = ip;

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

  return {
    success: data.success,
    errorCodes: data["error-codes"],
  };
}
