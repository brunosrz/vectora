/**
 * Next.js App Router catch-all — monta o Hono app em /api/**.
 *
 * O Hono é compatível com o runtime Edge e Node.js do Next.js.
 * Aqui usamos o adaptador para o runtime padrão (Node.js).
 */

import { handle } from "hono/vercel";
import app from "@/server";

export const runtime = "nodejs";

const handler = handle(app);

export const GET = handler;
export const POST = handler;
export const DELETE = handler;
export const PATCH = handler;
