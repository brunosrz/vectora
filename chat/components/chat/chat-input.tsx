/**
 * Chat Input Component
 *
 * Fixed input area at the bottom of the chat interface.
 * Includes file upload, drag & drop, and paste support.
 */

import { useCallback, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FilePreviewGrid } from "./features/file-preview-grid";
import { VoiceInputButton } from "./features/voice-input-button";
import { PermissionModeMenu } from "./features/permission-mode-menu";
import { ChatParamsMenu } from "./features/chat-params-menu";
import { PlusMenu } from "./features/plus-menu";
import { UsagePopover } from "./features/usage-popover";
import { SlashCommandMenu } from "./features/slash-command-menu";
import { AtMentionMenu } from "./features/at-mention-menu";
import { WorkspaceSelector } from "@/components/sidebar/workspace-selector";
import { ModelSelector } from "./model-selector";
import { VscodeIcon } from "@/components/icons/vscode-icon";
import { useWorkspacesStore } from "@/lib/stores/workspaces-store";
import type { SlashCommand } from "@/lib/constants/slash-commands";
import type { AgentConfig } from "@/components/layout/agent-settings";
import type { ImageAttachment } from "@/lib/types";
import { useT } from "@/lib/i18n";
import { useNetworkStatus } from "@/lib/hooks/use-network-status";

interface VscodeOption {
  strategy: string;
  label: string;
  url: string;
}

/** Botão "Abrir no VS Code" — opções dependem do workspace ativo. */
function VscodeMenu({ workspaceId }: { workspaceId: string }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const [options, setOptions] = useState<VscodeOption[]>([]);

  const handleOpen = useCallback(async () => {
    if (!workspaceId) return;
    const res = await fetch(
      `/workspaces/${encodeURIComponent(workspaceId)}/vscode-options`,
    );
    if (res.ok) {
      const data = await res.json();
      setOptions((data.options as VscodeOption[]) ?? []);
    }
    setOpen((v) => !v);
  }, [workspaceId]);

  return (
    <div className="relative">
      <button
        onClick={handleOpen}
        className="p-1.5 rounded-md text-muted-foreground hover:text-foreground hover:bg-muted/50 shrink-0"
        title={t("workbench.open_vscode")}
        aria-label={t("workbench.open_vscode")}
      >
        <VscodeIcon className="w-4 h-4" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute left-0 bottom-full mb-1 z-20 bg-popover border border-border/60 rounded-md shadow-lg py-1 min-w-[200px]">
            {options.length === 0 ? (
              <p className="px-3 py-1.5 text-xs text-muted-foreground">
                {t("workbench.open_vscode_unavailable")}
              </p>
            ) : (
              options.map((opt) => (
                <a
                  key={opt.strategy}
                  href={opt.url}
                  onClick={() => setOpen(false)}
                  className="flex items-center gap-2 px-3 py-1.5 text-xs hover:bg-muted/40 transition-colors"
                >
                  <VscodeIcon className="w-3 h-3 text-muted-foreground shrink-0" />
                  {opt.label}
                </a>
              ))
            )}
          </div>
        </>
      )}
    </div>
  );
}

interface ChatInputProps {
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onKeyDown: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  isLoading: boolean;
  isStopping: boolean;
  onStop: () => void;
  userId?: string | null;

  // File upload
  attachedFiles: ImageAttachment[];
  uploadError: string | null;
  inputError: string | null;
  isDragging: boolean;
  onDragOver: (e: React.DragEvent) => void;
  onDragLeave: (e: React.DragEvent) => void;
  onDrop: (e: React.DragEvent) => void;
  onPaste: (e: React.ClipboardEvent<HTMLTextAreaElement>) => void;
  onRemoveFile: (fileId: string) => void;
  onFileButtonClick: (e: React.MouseEvent) => void;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void;
  textareaRef?: React.RefObject<HTMLTextAreaElement | null>;

  // Voice input
  isVoiceListening?: boolean;
  isVoiceSupported?: boolean;
  onVoiceToggle?: () => void;
  voiceError?: string | null;

  // Queued messages
  queuedMessages?: { content: string; id: string }[];

  // Context meter (R5)
  tokensUsed?: number;
  modelId?: string;

  // Modelo (seletor permanente no rodapé) — F.2.2/F.2.3
  agentConfig?: AgentConfig;
  onAgentConfigChange?: (config: AgentConfig) => void;

  // F.2.3 — overlay de drop zone mais explícito no estado vazio
  dropHintExpanded?: boolean;
  /** Callback de seleção de arquivo via @mention. */
  onAtMentionSelect?: (path: string, startIdx: number, endIdx: number) => void;
}

const EMPTY_QUEUED_MESSAGES: NonNullable<ChatInputProps["queuedMessages"]> = [];

/**
 * Chat input area with file upload support.
 * Displays at the bottom of the chat interface when there are existing messages.
 */
export function ChatInput({
  input,
  onInputChange,
  onSend,
  onKeyDown,
  isLoading,
  isStopping,
  onStop,
  userId,
  attachedFiles,
  uploadError,
  inputError,
  isDragging,
  onDragOver,
  onDragLeave,
  onDrop,
  onPaste,
  onRemoveFile,
  onFileButtonClick,
  fileInputRef,
  onFileSelect,
  textareaRef,
  isVoiceListening,
  isVoiceSupported,
  onVoiceToggle,
  voiceError,
  queuedMessages = EMPTY_QUEUED_MESSAGES,
  tokensUsed,
  modelId,
  agentConfig,
  onAgentConfigChange,
  dropHintExpanded = false,
  onAtMentionSelect,
}: ChatInputProps) {
  const t = useT();
  const wsId = useWorkspacesStore((s) => s.getActive())?.id ?? "";
  // UX-16 — sem rede não há para onde enviar; desabilita entrada e ações
  // que dependem do backend (anexos, voz) em vez de deixar o usuário digitar
  // para uma falha certa.
  const { offline } = useNetworkStatus();
  const handleModelChange = (model: string) => {
    if (agentConfig && onAgentConfigChange) {
      onAgentConfigChange({ ...agentConfig, model });
    }
  };

  // Auto-grow do textarea: ajusta a altura ao conteúdo até o teto de 240px;
  // depois disso o próprio textarea passa a scrollar internamente. Resolve
  // a queixa "ele não expande pra cima e com scroll visível".
  useEffect(() => {
    const el = textareaRef?.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(240, el.scrollHeight);
    el.style.height = `${next}px`;
  }, [input, textareaRef]);
  return (
    <div className="relative">
      {/* Enhanced visibility layer */}
      <div className="absolute inset-0 pointer-events-none" />

      <div className="relative border-t border-border/60 bg-background backdrop-blur-sm">
        <div className="w-full max-w-4xl mx-auto px-3 sm:px-4 py-1.5">
          {/* File Previews */}
          <FilePreviewGrid files={attachedFiles} onRemove={onRemoveFile} />

          {/* Upload Error */}
          {uploadError && (
            <div className="mb-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
              {uploadError}
            </div>
          )}

          {/* Voice Error */}
          {voiceError && (
            <div className="mb-2 text-sm text-destructive bg-destructive/10 px-3 py-2 rounded-md">
              {voiceError}
            </div>
          )}

          {/* Queued Messages */}
          {queuedMessages.length > 0 && (
            <div className="mb-2 space-y-1.5">
              {queuedMessages.map((msg) => (
                <div
                  key={msg.id}
                  className="flex items-center gap-2 px-3 py-2 bg-muted/50 border border-border/50 rounded-lg text-sm"
                >
                  <div className="flex items-center gap-1.5 text-muted-foreground flex-shrink-0">
                    <svg
                      className="w-3 h-3 animate-pulse"
                      xmlns="http://www.w3.org/2000/svg"
                      viewBox="0 0 24 24"
                      fill="currentColor"
                    >
                      <circle cx="12" cy="12" r="10" />
                    </svg>
                    <span className="text-xs font-medium">
                      {t("input.queued")}
                    </span>
                  </div>
                  <span className="text-foreground/80 truncate">
                    {msg.content}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="relative group">
            {/* Autocomplete de @arquivo — aparece antes do slash para não conflitar */}
            {onAtMentionSelect && (
              <AtMentionMenu input={input} onSelect={onAtMentionSelect} />
            )}

            {/* Autocomplete de slash commands (Bloco H) */}
            <SlashCommandMenu
              input={input}
              onSelect={(cmd: SlashCommand) => {
                onInputChange(cmd.takesArg ? `/${cmd.name} ` : `/${cmd.name}`);
                textareaRef?.current?.focus();
              }}
            />

            {/* Multi-layered input container */}
            <div className="relative">
              {/* Glow de contraste — sem `shadow-*`: o Vectora não usa sombras
                  projetadas (vazavam para a appbar no tema claro). */}
              <div className="absolute -inset-1 bg-primary/8 rounded-2xl opacity-70 group-hover:opacity-90 group-focus-within:opacity-100 transition-opacity duration-300" />

              {/* Main input container with enhanced contrast */}
              <div
                className={`relative backdrop-blur-sm border-2 rounded-xl transition-all duration-300 group-focus-within:ring-2 group-focus-within:ring-primary/20 ${isDragging ? "border-primary bg-primary/5 ring-2 ring-primary/30" : "border-border/50 group-hover:border-primary/60 group-focus-within:border-primary/70"}`}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
              >
                {isDragging && (
                  <div
                    className={
                      dropHintExpanded
                        ? "absolute inset-0 bg-primary/15 rounded-xl flex items-center justify-center z-20 pointer-events-none border-2 border-dashed border-primary"
                        : "absolute inset-0 bg-primary/10 rounded-xl flex items-center justify-center z-20 pointer-events-none"
                    }
                  >
                    <div className="text-primary font-medium">
                      {t("welcome.drop_files")}
                    </div>
                  </div>
                )}
                <div className="flex items-end gap-2 px-3 py-1.5">
                  {/* Hidden File Input */}
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.py,.js,.ts,.tsx,.jsx,.java,.cpp,.c,.h,.cs,.go,.rs,.rb,.php,.sh,.bash,.yaml,.yml,.json,.xml,.html,.css,.md,.txt,.log,.sql,.graphql,.r,.swift,.kt,.scala,.har"
                    multiple
                    onChange={onFileSelect}
                    className="hidden"
                  />

                  {/* Menu + (anexos / pasta / comandos) — R3 */}
                  {!isLoading && (
                    <PlusMenu
                      disabled={!userId || offline}
                      onAddFiles={onFileButtonClick}
                    />
                  )}

                  <Textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => onInputChange(e.target.value)}
                    onKeyDown={onKeyDown}
                    onPaste={onPaste}
                    placeholder={
                      !userId
                        ? t("input.initializing")
                        : offline
                          ? t("network.disabled_offline")
                          : isLoading
                            ? t("input.loading_placeholder")
                            : t("input.placeholder")
                    }
                    title={offline ? t("network.disabled_offline") : undefined}
                    className="relative z-10 min-h-[36px] max-h-[240px] resize-none overflow-y-auto bg-transparent border-0 w-full px-3 py-2 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 transition-[height] duration-150 break-words custom-scrollbar"
                    disabled={!userId || offline}
                    rows={1}
                  />

                  {isVoiceSupported && onVoiceToggle && (
                    <VoiceInputButton
                      isListening={isVoiceListening ?? false}
                      disabled={!userId || offline}
                      onClick={onVoiceToggle}
                      size="sm"
                    />
                  )}

                  {isLoading && (
                    <Button
                      onClick={onStop}
                      variant="ghost"
                      size="sm"
                      disabled={isStopping}
                      className={`
                        h-9 px-4 mb-0.5 rounded-full flex-shrink-0
                        transition-all duration-200 hover:scale-105 active:scale-95
                        bg-muted text-primary hover:text-primary hover:bg-muted/80 border-2 border-primary
                        ${isStopping ? "opacity-60 cursor-not-allowed" : ""}
                      `}
                      type="button"
                      title={
                        isStopping
                          ? t("input.stopping")
                          : t("input.stop_generating")
                      }
                    >
                      <span className="text-xs font-medium">
                        {isStopping ? t("input.stopping") : t("input.stop")}
                      </span>
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </div>

          {inputError && (
            <div className="mt-1 px-2 text-xs text-destructive">
              {inputError}
            </div>
          )}

          {/* Rodapé do input — "meio-termo" entre o estilo Claude Code
              (dois grupos minimalistas) e a chip row do Codex (contexto →
              configuração). Grupo esquerdo: workspace (onde) → modo de
              permissão; direita: modelo e medidor de uso. Sem barra de
              contexto acima do input (poluição visual desnecessária). */}
          <div className="flex items-center justify-between gap-2 mt-1 px-1 flex-wrap">
            <div className="flex items-center gap-1 min-w-0">
              <WorkspaceSelector compact />
              {wsId && <VscodeMenu workspaceId={wsId} />}
              <div className="hidden sm:block h-4 w-px bg-border/60 mx-0.5" />
              <PermissionModeMenu />
            </div>

            <div className="flex items-center gap-1 flex-wrap justify-end">
              <ChatParamsMenu />
              {agentConfig && onAgentConfigChange && (
                <ModelSelector
                  value={agentConfig.model}
                  onChange={handleModelChange}
                  compact
                />
              )}
              {modelId && (
                <UsagePopover tokensUsed={tokensUsed ?? 0} modelId={modelId} />
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
