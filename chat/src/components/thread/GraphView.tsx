"use client";

/**
 * GraphView — visualização ao vivo do grafo LangGraph com @xyflow/react.
 *
 * Busca a topologia via GET /assistants/{assistant_id}/graph e renderiza
 * com React Flow. O nó ativo é destacado em laranja via `activeNode` prop,
 * que vem do metadata do stream SSE.
 *
 * D1.3 — Live Graph Visualization
 */

import {
  ReactFlow,
  Background,
  Controls,
  type Node,
  type Edge,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useState, useCallback } from "react";

interface GraphNode {
  id: string;
  data?: { label?: string };
}

interface GraphEdge {
  source: string;
  target: string;
  conditional?: boolean;
}

interface GraphSchema {
  nodes?: GraphNode[];
  edges?: GraphEdge[];
}

interface GraphViewProps {
  /** Nome do assistente (ex: "vectora") */
  assistantId: string;
  /** URL do servidor LangGraph */
  apiUrl: string;
  /** Nó atualmente em execução (extraído do stream metadata) */
  activeNode?: string | null;
  /** Latência por nó em ms */
  nodeMetrics?: Record<string, number>;
}

// Layout manual simples em colunas — LangGraph grafos tendem a ser lineares
function layoutNodes(raw: GraphNode[]): Node[] {
  const SPACING_X = 200;
  const SPACING_Y = 90;
  const colMap: Record<string, number> = {};
  let col = 0;

  return raw.map((n, idx): Node => {
    const x = (colMap[n.id] ?? (colMap[n.id] = col++)) * SPACING_X;
    return {
      id: n.id,
      position: { x, y: idx * SPACING_Y },
      data: { label: n.data?.label ?? n.id },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      style: {
        borderRadius: 8,
        fontSize: 12,
        padding: "6px 12px",
      },
    };
  });
}

function buildEdges(raw: GraphEdge[]): Edge[] {
  return raw.map(
    (e, idx): Edge => ({
      id: `e-${idx}-${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      animated: e.conditional ?? false,
      style: e.conditional ? { strokeDasharray: "5 5" } : {},
    }),
  );
}

export function GraphView({
  assistantId,
  apiUrl,
  activeNode,
  nodeMetrics,
}: GraphViewProps) {
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchGraph = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch(`${apiUrl}/assistants/${assistantId}/graph`, {
        headers: { Accept: "application/json" },
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const schema: GraphSchema = await res.json();
      setNodes(layoutNodes(schema.nodes ?? []));
      setEdges(buildEdges(schema.edges ?? []));
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [apiUrl, assistantId]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  // Highlight active node
  const styledNodes = nodes.map((n) => {
    const isActive = n.id === activeNode;
    const ms = nodeMetrics?.[n.id];
    return {
      ...n,
      data: {
        ...n.data,
        label: ms != null ? `${n.data.label} (${ms}ms)` : n.data.label,
      },
      style: {
        ...n.style,
        background: isActive ? "#f97316" : "#ffffff",
        color: isActive ? "#ffffff" : "#111827",
        border: isActive ? "2px solid #ea580c" : "1px solid #d1d5db",
        fontWeight: isActive ? 700 : 400,
        boxShadow: isActive ? "0 0 0 3px rgba(249,115,22,0.3)" : undefined,
        transition: "all 0.3s ease",
      },
    };
  });

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-gray-400">
        Carregando topologia do grafo…
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-2 text-sm text-gray-500 p-4">
        <p className="text-red-500 font-medium">Grafo indisponível</p>
        <p className="text-xs text-center opacity-70">
          Certifique-se de que <code>langgraph dev</code> está rodando e{" "}
          <code>langgraph.json</code> está configurado.
        </p>
        <button
          onClick={fetchGraph}
          className="mt-2 text-xs text-blue-600 hover:underline"
        >
          Tentar novamente
        </button>
      </div>
    );
  }

  if (nodes.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-sm text-gray-400">
        Nenhum nó encontrado no grafo.
      </div>
    );
  }

  return (
    <div style={{ height: "100%", width: "100%" }}>
      <ReactFlow
        nodes={styledNodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#f3f4f6" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
