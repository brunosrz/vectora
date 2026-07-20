/**
 * Producers das duas filas — wrappers finos sobre env.EMAIL_QUEUE/JOBS_QUEUE.
 * Existir como função (em vez de chamar .send() direto nos handlers) só pra
 * centralizar o tipo da mensagem num lugar só.
 */
import type { Env } from "../gateway/types";
import type { EmailMessage, JobMessage } from "./queue-types";

export async function enqueueEmail(
  env: Env,
  message: EmailMessage,
): Promise<void> {
  await env.EMAIL_QUEUE.send(message);
}

export async function enqueueJob(env: Env, message: JobMessage): Promise<void> {
  await env.JOBS_QUEUE.send(message);
}
