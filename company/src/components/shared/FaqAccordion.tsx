import * as Accordion from "@radix-ui/react-accordion";
import { ChevronDown } from "lucide-react";

export interface FaqItem {
  question: string;
  answer: string;
}

interface FaqAccordionProps {
  items: FaqItem[];
}

export default function FaqAccordion({ items }: FaqAccordionProps) {
  return (
    <Accordion.Root type="single" collapsible className="space-y-2">
      {items.map((item, i) => (
        <Accordion.Item
          key={i}
          value={String(i)}
          className="rounded-lg border border-brand-700 bg-brand-800 overflow-hidden"
        >
          <Accordion.Header>
            <Accordion.Trigger className="group flex w-full items-center justify-between px-5 py-4 text-left text-sm font-medium text-white transition-colors hover:text-brand-400 data-[state=open]:text-brand-400">
              <span>{item.question}</span>
              <ChevronDown
                size={16}
                className="shrink-0 text-slate-400 transition-transform duration-200 group-data-[state=open]:rotate-180"
              />
            </Accordion.Trigger>
          </Accordion.Header>
          <Accordion.Content className="overflow-hidden data-[state=closed]:animate-[slideUp_0.2s_ease] data-[state=open]:animate-[slideDown_0.2s_ease]">
            <div className="border-t border-brand-700 px-5 py-4 text-sm text-slate-400 leading-relaxed">
              {item.answer}
            </div>
          </Accordion.Content>
        </Accordion.Item>
      ))}
    </Accordion.Root>
  );
}
