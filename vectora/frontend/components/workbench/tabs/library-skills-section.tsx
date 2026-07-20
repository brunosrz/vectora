"use client";

/**
 * SkillsSection — seção "Skills" da Library (Sprint 3): migra a
 * funcionalidade da antiga aba Settings → Skills (backend/workspace/
 * skills.py, GET/POST /skills, DELETE /skills/:id, POST /skills/:id/verify)
 * pra dentro da Library. Reaproveita o componente SkillsTab existente —
 * mesma tela hoje em Settings → Skills, que sai de lá no Sprint 4 — e usa
 * seu callback onSkillsChange pra manter o badge "(N)" do accordion em dia
 * sem duplicar o fetch.
 *
 * Um catálogo curado de skills populares (análogo ao _REGISTRY do MCP
 * marketplace) ficou fora desta sprint: publicar uma lista de URLs git
 * "populares" sem poder verificar que cada uma é um repositório real e
 * seguro seria fabricar conteúdo, não migrar uma funcionalidade — fica
 * como evolução futura, condicionada a uma fonte curada de verdade (ex.
 * o registry do Worker, hoje um placeholder vazio).
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
