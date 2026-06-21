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
        <div className="absolute left-3 top-1/2 -translate-y-1/2 z-10">
          <Search className="w-4 h-4 text-muted-foreground/70 group-focus-within:text-primary transition-all duration-200" />
        </div>
        <Input
          type="search"
          name="sessions-search-x"
          placeholder={m.sidebar_search_placeholder()}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete="off"
          className="pl-10 pr-8 h-10 text-sm bg-background/80 backdrop-blur-sm border-border/40 focus:border-primary/60 focus:bg-background/90 focus:shadow-sm transition-all duration-200 shadow-sm hover:shadow-md hover:bg-background/90 rounded-lg"
        />
        {value && (
          <button
            type="button"
            onClick={onClear}
            aria-label={m.sidebar_clear_search()}
            className="absolute right-3 top-1/2 -translate-y-1/2 z-10 text-muted-foreground/60 hover:text-foreground transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-primary/30 rounded-full p-0.5 hover:bg-muted/50"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
});
