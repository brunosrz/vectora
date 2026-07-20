"use client";

/**
 * LibraryTab — shell da aba Library (Sprint 1): 3 seções fecháveis (MCP,
 * Skills, Memory Library) + busca com filtros toggle por categoria.
 *
 * Cada seção povoa seus próprios itens nos Sprints 2 (MCP), 3 (Skills) e 6
 * (Memory Library) — aqui só o shell + o mecanismo de busca/filtro, que já
 * funciona sobre os itens conforme cada seção for entrando (busca
 * client-side sobre os dados já carregados, sem endpoint agregado).
 */

import { Blocks, Library as LibraryIcon, Puzzle, Search } from "lucide-react";
import { useMemo, useState } from "react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { m } from "@/lib/paraglide/messages";

interface LibraryTabProps {
  threadId: string;
}

type LibraryFilter = "mcp" | "skills" | "memory";

const ALL_FILTERS: LibraryFilter[] = ["mcp", "skills", "memory"];

/** Item genérico de qualquer seção — cada seção real (Sprints 2/3/6) monta
 * a lista completa a partir do seu próprio backend; a busca/filtro aqui só
 * precisa do nome pra combinar contra a query. */
export interface LibraryItem {
  id: string;
  name: string;
  description?: string;
}

function FilterPill({
  label,
  active,
  onToggle,
}: {
  label: string;
  active: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={active}
      className={`text-xs px-2.5 py-1 rounded-full transition-colors ${
        active
          ? "bg-primary/15 text-primary"
          : "bg-muted text-muted-foreground hover:text-foreground hover:bg-muted/80"
      }`}
    >
      {label}
    </button>
  );
}

function LibrarySearchBox({
  query,
  onChange,
}: {
  query: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="relative min-w-0 flex-1">
      <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
      <input
        type="text"
        value={query}
        onChange={(e) => onChange(e.target.value)}
        placeholder={m.library_search_placeholder()}
        className="w-full rounded-lg border border-border/60 bg-card/30 py-1.5 pl-7 pr-2.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary/50"
      />
    </div>
  );
}

function filterItems(items: LibraryItem[], query: string): LibraryItem[] {
  const q = query.trim().toLowerCase();
  if (!q) return items;
  return items.filter(
    (item) =>
      item.name.toLowerCase().includes(q) ||
      (item.description?.toLowerCase().includes(q) ?? false),
  );
}

function SectionEmptyState({ label }: { label: string }) {
  return (
    <p className="py-4 text-xs text-muted-foreground text-center">{label}</p>
  );
}

export function LibraryTab({ threadId }: LibraryTabProps) {
  void threadId;
  const [query, setQuery] = useState("");
  const [activeFilters, setActiveFilters] = useState<Set<LibraryFilter>>(
    new Set(ALL_FILTERS),
  );

  const toggleFilter = (filter: LibraryFilter) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(filter)) {
        next.delete(filter);
      } else {
        next.add(filter);
      }
      return next;
    });
  };

  // Seções ainda vazias (Sprints 2/3/6 povoam cada uma) — a busca/filtro já
  // funciona sobre a lista real assim que ela existir.
  const mcpItems = useMemo<LibraryItem[]>(() => [], []);
  const skillsItems = useMemo<LibraryItem[]>(() => [], []);
  const memoryItems = useMemo<LibraryItem[]>(() => [], []);

  const filteredMcp = filterItems(mcpItems, query);
  const filteredSkills = filterItems(skillsItems, query);
  const filteredMemory = filterItems(memoryItems, query);

  const noFiltersActive = activeFilters.size === 0;

  return (
    <div className="h-full flex flex-col">
      <div className="p-3 space-y-2 border-b border-border/60">
        <LibrarySearchBox query={query} onChange={setQuery} />
        <div className="flex flex-wrap gap-1.5">
          <FilterPill
            label={m.library_filter_mcp()}
            active={activeFilters.has("mcp")}
            onToggle={() => toggleFilter("mcp")}
          />
          <FilterPill
            label={m.library_filter_skills()}
            active={activeFilters.has("skills")}
            onToggle={() => toggleFilter("skills")}
          />
          <FilterPill
            label={m.library_filter_memory()}
            active={activeFilters.has("memory")}
            onToggle={() => toggleFilter("memory")}
          />
        </div>
      </div>

      <div className="flex-1 overflow-y-auto min-h-0">
        {noFiltersActive ? (
          <SectionEmptyState label={m.library_empty_no_filters()} />
        ) : (
          <Accordion
            type="multiple"
            defaultValue={["mcp", "skills", "memory"]}
            className="px-1"
          >
            {activeFilters.has("mcp") && (
              <AccordionItem value="mcp">
                <AccordionTrigger>
                  <span className="flex items-center gap-2 min-w-0">
                    <Puzzle className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">
                      {m.library_section_mcp()} ({filteredMcp.length})
                    </span>
                  </span>
                </AccordionTrigger>
                <AccordionContent>
                  {filteredMcp.length === 0 ? (
                    <SectionEmptyState label={m.library_empty_mcp()} />
                  ) : (
                    <ul className="divide-y divide-border/30">
                      {filteredMcp.map((item) => (
                        <li key={item.id} className="py-1.5 text-xs">
                          {item.name}
                        </li>
                      ))}
                    </ul>
                  )}
                </AccordionContent>
              </AccordionItem>
            )}

            {activeFilters.has("skills") && (
              <AccordionItem value="skills">
                <AccordionTrigger>
                  <span className="flex items-center gap-2 min-w-0">
                    <Blocks className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">
                      {m.library_section_skills()} ({filteredSkills.length})
                    </span>
                  </span>
                </AccordionTrigger>
                <AccordionContent>
                  {filteredSkills.length === 0 ? (
                    <SectionEmptyState label={m.library_empty_skills()} />
                  ) : (
                    <ul className="divide-y divide-border/30">
                      {filteredSkills.map((item) => (
                        <li key={item.id} className="py-1.5 text-xs">
                          {item.name}
                        </li>
                      ))}
                    </ul>
                  )}
                </AccordionContent>
              </AccordionItem>
            )}

            {activeFilters.has("memory") && (
              <AccordionItem value="memory">
                <AccordionTrigger>
                  <span className="flex items-center gap-2 min-w-0">
                    <LibraryIcon className="w-3.5 h-3.5 shrink-0 text-muted-foreground" />
                    <span className="truncate">
                      {m.library_section_memory()} ({filteredMemory.length})
                    </span>
                  </span>
                </AccordionTrigger>
                <AccordionContent>
                  {filteredMemory.length === 0 ? (
                    <SectionEmptyState label={m.library_empty_memory()} />
                  ) : (
                    <ul className="divide-y divide-border/30">
                      {filteredMemory.map((item) => (
                        <li key={item.id} className="py-1.5 text-xs">
                          {item.name}
                        </li>
                      ))}
                    </ul>
                  )}
                </AccordionContent>
              </AccordionItem>
            )}
          </Accordion>
        )}
      </div>
    </div>
  );
}
