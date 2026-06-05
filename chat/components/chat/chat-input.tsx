/**
 * Chat Input Component
 *
 * Fixed input area at the bottom of the chat interface.
 * Includes file upload, drag & drop, and paste support.
 */

import { useEffect } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FilePreviewGrid } from "./features/file-preview-grid";
import { VoiceInputButton } from "./features/voice-input-button";
import { PermissionModeMenu } from "./features/permission-mode-menu";
import { PlusMenu } from "./features/plus-menu";
import { UsagePopover } from "./features/usage-popover";
import { SlashCommandMenu } from "./features/slash-command-menu";
import { AtMentionMenu } from "./features/at-mention-menu";
import type { SlashCommand } from "@/lib/constants/slash-commands";
import type { AgentConfig } from "@/components/layout/agent-settings";
import {
  getAllowedModels,
  getModelDisplayName,
  type ModelOption,
} from "@/lib/config/deployment-config";
import type { ImageAttachment } from "@/lib/types";
import { useT } from "@/lib/i18n";

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
  const allowedModels = getAllowedModels();
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
              {/* High-contrast glow layer for visibility */}
              <div className="absolute -inset-1 bg-primary/8 rounded-2xl opacity-70 group-hover:opacity-90 group-focus-within:opacity-100 transition-opacity duration-300 shadow-2xl" />

              {/* Main input container with enhanced contrast */}
              <div
                className={`relative backdrop-blur-sm border-2 rounded-xl shadow-2xl transition-all duration-300 group-hover:shadow-3xl group-focus-within:shadow-3xl group-focus-within:ring-2 group-focus-within:ring-primary/20 ${isDragging ? "border-primary bg-primary/5 ring-2 ring-primary/30" : "border-border/50 group-hover:border-primary/60 group-focus-within:border-primary/70"}`}
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
                      disabled={!userId}
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
                        : isLoading
                          ? t("input.loading_placeholder")
                          : t("input.placeholder")
                    }
                    className="relative z-10 min-h-[36px] max-h-[240px] resize-none overflow-y-auto bg-transparent border-0 w-full px-3 py-2 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 transition-[height] duration-150 break-words custom-scrollbar"
                    disabled={!userId}
                    rows={1}
                  />

                  {isVoiceSupported && onVoiceToggle && (
                    <VoiceInputButton
                      isListening={isVoiceListening ?? false}
                      disabled={!userId}
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

          {/* Rodapé do input no estilo Claude Code: modelo à esquerda,
              modo de permissão e medidor de uso à direita. Sem barra de
              contexto acima do input (poluição visual desnecessária). */}
          <div className="flex items-center justify-between gap-2 mt-1 px-1 flex-wrap">
            <div className="flex items-center gap-1 min-w-0">
              {agentConfig && onAgentConfigChange && (
                <Select
                  value={agentConfig.model}
                  onValueChange={handleModelChange}
                >
                  <SelectTrigger className="h-7 text-xs border-0 bg-transparent hover:text-foreground px-2 gap-1 w-auto shadow-none focus:ring-0 focus-visible:ring-0 text-muted-foreground [&_svg]:opacity-70">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {allowedModels.map((model) => (
                      <SelectItem key={model} value={model}>
                        {getModelDisplayName(model as ModelOption)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>

            <div className="flex items-center gap-1 flex-wrap justify-end">
              <PermissionModeMenu />
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
