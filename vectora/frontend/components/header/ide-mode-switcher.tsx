"use client";

import { Bot, Code2, KanbanSquare } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useSettingsStore } from "@/lib/stores/settings-store";
import { useFeatureFlags } from "@/lib/hooks/use-feature-flags";
import { useElementWidth } from "@/lib/hooks/use-element-width";
import { m } from "@/lib/paraglide/messages";
import type { UiMode } from "@/lib/stores/settings-store";

interface IdeModeProps {
  show?: boolean;
}

//: Larguras medidas empiricamente contra o conteúdo real dos 3 botões —
//: abaixo de `TRUNCATE_BELOW` o texto começa a colidir com o vizinho no
//: header antes do CSS truncar sozinho; abaixo de `ICON_ONLY_BELOW` nem o
//: texto truncado cabe sem cortar o ícone.
const TRUNCATE_BELOW = 260;
const ICON_ONLY_BELOW = 160;

//: Cor de destaque só no estado ativo — inativo fica neutro pra não brigar
//: com o resto do header (mesmo princípio de contenção visual do HITLPanel).
const MODE_ACTIVE_CLASS: Record<UiMode, string> = {
  assistant: "bg-blue-500/10 text-blue-400 font-medium",
  ide: "bg-violet-500/10 text-violet-400 font-medium",
  kanban: "bg-amber-500/10 text-amber-400 font-medium",
};

function ModeButton({
  mode,
  active,
  onClick,
  Icon,
  label,
  labelSize,
}: {
  mode: UiMode;
  active: boolean;
  onClick: () => void;
  Icon: LucideIcon;
  label: string;
  labelSize: "full" | "truncated" | "icon";
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      title={label}
      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs transition-colors min-w-0 ${
        active
          ? MODE_ACTIVE_CLASS[mode]
          : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
      }`}
    >
      <Icon className="w-3.5 h-3.5 shrink-0" />
      <span
        className={
          labelSize === "icon"
            ? "sr-only"
            : labelSize === "truncated"
              ? "truncate max-w-[3.5rem]"
              : ""
        }
      >
        {label}
      </span>
    </button>
  );
}

export function IdeModeSwitch({ show = false }: IdeModeProps) {
  const uiMode = useSettingsStore((s) => s.uiMode);
  const setUiMode = useSettingsStore((s) => s.setUiMode);
  const { enableKanbanMode } = useFeatureFlags();
  const [ref, width] = useElementWidth<HTMLDivElement>();

  if (!show) return null;

  const labelSize =
    width >= TRUNCATE_BELOW
      ? "full"
      : width >= ICON_ONLY_BELOW
        ? "truncated"
        : "icon";

  return (
    // Mede este wrapper, não o grupo de botões dentro dele — o grupo encolhe
    // ao próprio conteúdo (shrink-to-fit), então medir ele diretamente
    // convergiria sempre pro estado mínimo (ícone-only). O wrapper com
    // `flex-1` é quem de fato reflete o espaço disponível no header.
    <div ref={ref} className="min-w-0 flex-1 flex justify-center">
      <div
        role="group"
        aria-label={m.ide_mode_switcher_label()}
        className="flex rounded-lg border border-border/40 overflow-hidden min-w-0"
      >
        <ModeButton
          mode="assistant"
          active={uiMode === "assistant"}
          onClick={() => {
            if (uiMode !== "assistant") setUiMode("assistant");
          }}
          Icon={Bot}
          label={m.ide_mode_assistente()}
          labelSize={labelSize}
        />
        <div className="w-px bg-border/40 self-stretch" />
        <ModeButton
          mode="ide"
          active={uiMode === "ide"}
          onClick={() => {
            if (uiMode !== "ide") setUiMode("ide");
          }}
          Icon={Code2}
          label={m.ide_mode_ide()}
          labelSize={labelSize}
        />
        {/* Fora do dev mode o seletor continua binário — o usuário comum não
            vê a opção existir, em vez de vê-la desabilitada. */}
        {enableKanbanMode && (
          <>
            <div className="w-px bg-border/40 self-stretch" />
            <ModeButton
              mode="kanban"
              active={uiMode === "kanban"}
              onClick={() => {
                if (uiMode !== "kanban") setUiMode("kanban");
              }}
              Icon={KanbanSquare}
              label={m.ide_mode_kanban()}
              labelSize={labelSize}
            />
          </>
        )}
      </div>
    </div>
  );
}
