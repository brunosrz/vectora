import { request, type FullConfig } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { dirname } from "node:path";

/**
 * Autentica uma vez e salva o storageState (cookie httpOnly `vectora_access`)
 * para todos os testes reusarem — evita repetir login por teste.
 *
 * Fluxo: consulta `/auth/has-users`; se não houver usuários, cria o root via
 * `/auth/signup`; caso contrário, faz `/auth/signin`. As credenciais vêm de
 * E2E_EMAIL / E2E_PASSWORD (com defaults locais).
 */
const BASE_URL = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:5173";
const EMAIL = process.env.E2E_EMAIL ?? "e2e@vectora.local";
const PASSWORD = process.env.E2E_PASSWORD ?? "Vectora-e2e-2026!";
const STATE_PATH = "./e2e/.auth/state.json";

async function globalSetup(_config: FullConfig): Promise<void> {
  const ctx = await request.newContext({ baseURL: BASE_URL });

  const hasUsersRes = await ctx.get("/auth/has-users");
  if (!hasUsersRes.ok()) {
    throw new Error(
      `e2e setup: /auth/has-users falhou (${hasUsersRes.status()}). ` +
        "O backend do Vectora está rodando em :8080?",
    );
  }
  const { exists: hasUsers } = (await hasUsersRes.json()) as {
    exists: boolean;
  };

  const endpoint = hasUsers ? "/auth/signin" : "/auth/signup";
  const payload = hasUsers
    ? { email: EMAIL, password: PASSWORD }
    : { name: "E2E", email: EMAIL, password: PASSWORD };

  const authRes = await ctx.post(endpoint, { data: payload });
  if (!authRes.ok()) {
    const body = await authRes.text().catch(() => "");
    throw new Error(
      `e2e setup: ${endpoint} falhou (${authRes.status()}): ${body}\n` +
        "Defina E2E_EMAIL/E2E_PASSWORD que batam com um usuário existente, " +
        "ou aponte para um backend limpo (sem usuários) para criar o root.",
    );
  }

  mkdirSync(dirname(STATE_PATH), { recursive: true });
  await ctx.storageState({ path: STATE_PATH });
  await ctx.dispose();
}

export default globalSetup;
