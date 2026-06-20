"use client";

import { m as msg } from "@/lib/paraglide/messages";
import { useAdministracaoDialogStore } from "@/lib/stores/administracao-dialog-store";
import { useEnvironmentDialogStore } from "@/lib/stores/environment-dialog-store";
import { usePreferenciasDialogStore } from "@/lib/stores/preferencias-dialog-store";

type SettingsGroup = "preferencias" | "environment" | "admin";

interface Props {
  active: SettingsGroup;
}

export function SettingsGroupTabs({ active }: Props) {
  const openPref = usePreferenciasDialogStore((s) => s.openAt);
  const closePref = usePreferenciasDialogStore((s) => s.setOpen);
  const openEnv = useEnvironmentDialogStore((s) => s.openAt);
  const closeEnv = useEnvironmentDialogStore((s) => s.setOpen);
  const openAdmin = useAdministracaoDialogStore((s) => s.openAt);
  const closeAdmin = useAdministracaoDialogStore((s) => s.setOpen);

  function switchTo(group: SettingsGroup) {
    if (group === active) return;
    closePref(false);
    closeEnv(false);
    closeAdmin(false);
    if (group === "preferencias") openPref();
    else if (group === "environment") openEnv();
    else openAdmin();
  }

  const groups: { id: SettingsGroup; label: string }[] = [
    { id: "preferencias", label: msg.settings_group_preferencias() },
    { id: "environment", label: msg.settings_group_environment() },
    { id: "admin", label: msg.settings_group_admin() },
  ];

  return (
    <div className="flex gap-1 border-b pb-2 mb-1 -mt-1">
      {groups.map(({ id, label }) => {
        const isActive = id === active;
        return (
          <button
            key={id}
            type="button"
            aria-current={isActive ? "page" : undefined}
            onClick={() => switchTo(id)}
            className={
              isActive
                ? "text-sm font-semibold text-foreground px-2 py-0.5 rounded"
                : "text-sm text-muted-foreground hover:text-foreground px-2 py-0.5 rounded transition-colors cursor-pointer"
            }
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}
