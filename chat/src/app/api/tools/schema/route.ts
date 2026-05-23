/**
 * GET /api/tools/schema
 *
 * Proxy server-side para o endpoint de schema do servidor Vectora MCP.
 * Evita CORS no browser — a chamada sai do servidor Next.js, não do cliente.
 *
 * Configuração (opcional): VECTORA_MCP_URL=http://localhost:8000
 * Se o servidor MCP não estiver rodando, retorna lista vazia sem erro.
 */

import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

export async function GET() {
  const mcpUrl = process.env.VECTORA_MCP_URL ?? "http://localhost:8000";

  try {
    const res = await fetch(`${mcpUrl}/api/tools/schema`, {
      headers: { Accept: "application/json" },
      // Timeout curto — não queremos bloquear o frontend se o MCP não estiver rodando
      signal: AbortSignal.timeout(2000),
    });

    if (!res.ok) {
      return NextResponse.json({ tools: [] });
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    // MCP server não está rodando — retorna lista vazia (frontend usa schema estático)
    return NextResponse.json({ tools: [] });
  }
}
