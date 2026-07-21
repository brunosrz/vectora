"use client";

/**
 * SkillsSection — gerencia skills instaladas (backend/workspace/skills.py,
 * GET/POST /skills, DELETE /skills/:id, POST /skills/:id/verify).
 * Reaproveita o componente SkillsTab, usando seu callback onSkillsChange
 * pra manter o badge "(N)" do accordion em dia sem duplicar o fetch.
 */

import { SkillsTab } from "@/components/settings/environment/tabs/skills-tab";

export function SkillsSection({
  onCountChange,
}: {
  query: string;
  onCountChange: (count: number) => void;
}) {
  return <SkillsTab onSkillsChange={onCountChange} />;
}
