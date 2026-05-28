"use client";

/**
 * HITLPanel — Painel de aprovação Human-in-the-Loop (Bloco E).
 *
 * Renderizado dentro de uma mensagem do assistente quando o stream pausa
 * para confirmação do usuário antes de executar uma tool destrutiva
 * (terminal, file_write, etc.).
 *
 * Ações:
 *   Approve — continua com os args originais
 *   Edit    — abre editor JSON para modificar args antes de executar
 *   Reject  — cancela; o agente recebe feedback de rejeição
 */

import { useState } from "react";
import { Check, X, Edit3, ChevronDown, ChevronRight, Terminal, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

// ===========================================================================
// Types
// ===========================================================================

export interface HITLPendingInfo {
  toolName: string;
  argsJson: string;
  interruptId: string;
}

interface HITLPanelProps {
  messageId: string;
  pending: HITLPendingInfo;
  threadId: string;
  onDecision: (messageId: string, interruptId: string, decision: "approve" | "reject" | `edit:${string}`) => void;
}

// ===========================================================================
// Helpers
// ===========================================================================

function prettyJson(json: string): string {
  try {
    return JSON.stringify(JSON.parse(json), null, 2);
  } catch {
    return json;
  }
}

function ToolIcon({ name }: { name: string }) {
  if (name === "terminal" || name === "terminal_tool") {
    return <Terminal className="w-4 h-4 text-orange-400" />;
  }
  return <FileText className="w-4 h-4 text-orange-400" />;
}

// ===========================================================================
// Component
// ===========================================================================

export function HITLPanel({ messageId, pending, onDecision }: HITLPanelProps) {
  const [showArgs, setShowArgs] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedArgs, setEditedArgs] = useState(prettyJson(pending.argsJson));
  const [editError, setEditError] = useState<string | null>(null);
  const [decided, setDecided] = useState(false);

  if (decided) return null;

  const handleApprove = () => {
    setDecided(true);
    onDecision(messageId, pending.interruptId, "approve");
  };

  const handleReject = () => {
    setDecided(true);
    onDecision(messageId, pending.interruptId, "reject");
  };

  const handleEditSubmit = () => {
    try {
      // Valida JSON antes de enviar
      JSON.parse(editedArgs);
      setEditError(null);
      setDecided(true);
      onDecision(messageId, pending.interruptId, `edit:${editedArgs.replace(/\s+/g, " ")}`);
    } catch {
      setEditError("JSON inválido — verifique a sintaxe antes de enviar.");
    }
  };

  const toolLabel = pending.toolName === "terminal" || pending.toolName === "terminal_tool" ? "terminal" : pending.toolName === "file_write" || pending.toolName === "file_write_tool" ? "file_write" : pending.toolName;

  return (
    <div className="mt-3 rounded-lg border border-orange-400/30 bg-orange-950/20 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-orange-400/20">
        <ToolIcon name={pending.toolName} />
        <span className="text-sm font-medium text-orange-300">Ação requer aprovação</span>
        <code className="ml-1 text-xs bg-orange-900/40 text-orange-200 px-1.5 py-0.5 rounded">{toolLabel}</code>
      </div>

      {/* Args preview / editor */}
      <div className="px-4 py-3">
        {!isEditing ? (
          <>
            <button onClick={() => setShowArgs((v) => !v)} className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors mb-2">
              {showArgs ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
              {showArgs ? "Ocultar" : "Ver"} argumentos
            </button>

            {showArgs && <pre className="text-xs bg-black/30 rounded p-3 overflow-x-auto text-green-300 font-mono mb-3">{prettyJson(pending.argsJson)}</pre>}
          </>
        ) : (
          <div className="mb-3">
            <p className="text-xs text-muted-foreground mb-2">Edite os argumentos em JSON antes de executar:</p>
            <Textarea
              value={editedArgs}
              onChange={(e) => {
                setEditedArgs(e.target.value);
                setEditError(null);
              }}
              className="font-mono text-xs min-h-[120px] bg-black/30 text-green-300 border-orange-400/30 resize-y"
              spellCheck={false}
            />
            {editError && <p className="text-xs text-red-400 mt-1">{editError}</p>}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          {!isEditing ? (
            <>
              <Button size="sm" variant="default" className="h-7 px-3 bg-green-600 hover:bg-green-500 text-white text-xs" onClick={handleApprove}>
                <Check className="w-3 h-3 mr-1" />
                Aprovar
              </Button>
              <Button size="sm" variant="outline" className="h-7 px-3 border-orange-400/40 text-orange-300 hover:bg-orange-900/30 text-xs" onClick={() => setIsEditing(true)}>
                <Edit3 className="w-3 h-3 mr-1" />
                Editar
              </Button>
              <Button size="sm" variant="outline" className="h-7 px-3 border-red-400/40 text-red-400 hover:bg-red-900/20 text-xs" onClick={handleReject}>
                <X className="w-3 h-3 mr-1" />
                Rejeitar
              </Button>
            </>
          ) : (
            <>
              <Button size="sm" variant="default" className="h-7 px-3 bg-green-600 hover:bg-green-500 text-white text-xs" onClick={handleEditSubmit}>
                <Check className="w-3 h-3 mr-1" />
                Executar editado
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="h-7 px-3 text-xs text-muted-foreground"
                onClick={() => {
                  setIsEditing(false);
                  setEditedArgs(prettyJson(pending.argsJson));
                  setEditError(null);
                }}
              >
                Cancelar edição
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
