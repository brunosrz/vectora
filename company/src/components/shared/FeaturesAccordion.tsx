/**
 * FeaturesAccordion — lista de features no estilo changelog: título +
 * resumo sempre visíveis, descrição completa some por trás de um
 * "expandir" (mesmo mecanismo do FaqAccordion, com um ícone por
 * categoria em vez de só texto).
 */

import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";
import type { LucideIcon } from "lucide-react";

export interface FeatureItem {
  id: string;
  Icon: LucideIcon;
  title: string;
  summary: string;
  description: string;
}

interface FeaturesAccordionProps {
  items: FeatureItem[];
}

export default function FeaturesAccordion({ items }: FeaturesAccordionProps) {
  return (
    <Accordion.Root type="single" collapsible className="space-y-2">
      {items.map((item) => {
        const { Icon } = item;
        return (
          <Accordion.Item
            key={item.id}
            value={item.id}
            className="rounded-lg border border-border bg-card overflow-hidden"
          >
            <Accordion.Header>
              <Accordion.Trigger className="group flex w-full items-start gap-3 px-5 py-4 text-left transition-colors hover:text-primary data-[state=open]:text-primary">
                <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <Icon className="h-4 w-4 text-primary" />
                </span>
                <span className="flex-1 min-w-0">
                  <span className="block text-sm font-medium text-foreground group-data-[state=open]:text-primary">
                    {item.title}
                  </span>
                  <span className="mt-0.5 block text-sm text-muted-foreground">
                    {item.summary}
                  </span>
                </span>
                <ChevronDown
                  size={16}
                  className="mt-1.5 shrink-0 text-muted-foreground transition-transform duration-200 group-data-[state=open]:rotate-180"
                />
              </Accordion.Trigger>
            </Accordion.Header>
            <Accordion.Content className="overflow-hidden data-[state=closed]:animate-[slideUp_0.2s_ease] data-[state=open]:animate-[slideDown_0.2s_ease]">
              <div className="border-t border-border px-5 py-4 pl-[3.75rem] text-sm text-muted-foreground leading-relaxed">
                {item.description}
              </div>
            </Accordion.Content>
          </Accordion.Item>
        );
      })}
    </Accordion.Root>
  );
}
