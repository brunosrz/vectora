/**
 * Formas de mensagem das duas filas do Worker. Sem imports — evita ciclo
 * com relay/types.ts, que importa estes tipos pra tipar Env.EMAIL_QUEUE/
 * Env.JOBS_QUEUE.
 */

export interface EmailMessage {
  to: string;
  subject: string;
  html: string;
}

export interface UpdateTelemetryJob {
  type: "update_telemetry";
  state: "started" | "completed" | "failed";
  version: string;
  os: string;
  arch: string;
}

export interface GdprDeleteUserJob {
  type: "gdpr_delete_user";
  userId: string;
}

export interface TelemetryIngestJob {
  type: "telemetry_ingest";
  source: string;
  eventType: string;
  payload: unknown;
}

export interface RagReindexJob {
  type: "rag_reindex";
  packageId: string;
}

export type JobMessage =
  | UpdateTelemetryJob
  | GdprDeleteUserJob
  | TelemetryIngestJob
  | RagReindexJob;
