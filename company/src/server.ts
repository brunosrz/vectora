import { paraglideMiddleware } from "#/paraglide/server.js";
import handler from "@tanstack/react-start/server-entry";

// deLocaliza a URL (ex.: /en/downloads -> /downloads) antes do handler do
// TanStack Start rotear — sem isso o router não reconhece o prefixo de
// locale e cai no Not Found. Usa o request ORIGINAL (não o `request`
// devolvido pelo callback), porque o router já faz sua própria
// deLocalização via `rewrite` em router.tsx; passar o já-deLocalizado de
// novo causaria um loop de redirect.
export default {
  fetch(req: Request): Promise<Response> {
    return paraglideMiddleware(req, () => handler.fetch(req));
  },
};
