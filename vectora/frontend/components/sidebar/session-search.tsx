"use client";

import { memo } from "react";
import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { m } from "@/lib/paraglide/messages";

interface SessionSearchProps {
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
}

export const SessionSearch = memo(function SessionSearch({
  value,
  onChange,
  onClear,
}: SessionSearchProps) {
  return (
    <div className="px-3 py-1.5">
      <div className="relative group">
        <div className="absolute left-2.5 top-1/2 -translate-y-1/2 z-10">
          <Search className="w-3.5 h-3.5 text-muted-foreground/60 group-focus-within:text-muted-foreground transition-colors duration-150" />
        </div>
        <Input
          type="search"
          name="sessions-search-x"
          placeholder={m.sidebar_search_placeholder()}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete="off"
          className="pl-8 pr-7 h-8 text-xs bg-background/60 border-border/40 focus:border-border/70 focus:bg-background/80 transition-colors duration-150 rounded-md"
        />
        {value && (
          <button
            type="button"
            onClick={onClear}
            aria-label={m.sidebar_clear_search()}
            className="absolute right-2 top-1/2 -translate-y-1/2 z-10 text-muted-foreground/50 hover:text-foreground transition-colors duration-150 focus:outline-none rounded p-0.5 hover:bg-muted/50"
          >
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
});
