import type { Env as WorkerEnv } from "../src/relay/types";

// `cloudflare:test`'s `env` export is typed as the ambient `Cloudflare.Env`
// (declared empty by @cloudflare/workers-types). Sem essa augmentation,
// `env.DB`/`env.RELAY_SESSION`/etc não tipam em nenhum teste.
declare global {
  namespace Cloudflare {
    interface Env extends WorkerEnv {}
  }
}

export {};
