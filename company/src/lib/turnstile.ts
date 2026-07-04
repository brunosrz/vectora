// Cloudflare Turnstile — proteção bot sem fricção para o usuário
// https://developers.cloudflare.com/turnstile/
//
// Só a chave pública do site vive aqui — a verificação do token acontece em
// services (server-to-server), não em company.

export const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY as
  | string
  | undefined;
