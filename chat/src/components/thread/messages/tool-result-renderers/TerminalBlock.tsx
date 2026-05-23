"use client";

/**
 * TerminalBlock — renderiza saída de terminal.
 *
 * Usado para `render_hint: "terminal_output"`.
 * Fundo escuro, monospace, scrollável.
 */

interface TerminalBlockProps {
  content: string;
  command?: string;
}

export function TerminalBlock({ content, command }: TerminalBlockProps) {
  const lines = content.split("\n");

  return (
    <div className="rounded-md overflow-hidden border border-gray-700 text-sm font-mono">
      {/* Terminal chrome */}
      <div className="flex items-center gap-1.5 px-3 py-2 bg-gray-900">
        <span className="w-3 h-3 rounded-full bg-red-500/80" />
        <span className="w-3 h-3 rounded-full bg-yellow-500/80" />
        <span className="w-3 h-3 rounded-full bg-green-500/80" />
        {command && (
          <span className="ml-2 text-xs text-gray-400 truncate">
            $ {command}
          </span>
        )}
      </div>
      {/* Output */}
      <div className="bg-gray-950 p-3 overflow-x-auto max-h-[350px] overflow-y-auto">
        {lines.map((line, idx) => (
          <div key={idx} className="text-xs leading-relaxed">
            {line ? (
              <span
                className={
                  line.toLowerCase().includes("error") ||
                  line.toLowerCase().includes("traceback")
                    ? "text-red-400"
                    : line.toLowerCase().includes("warning")
                      ? "text-yellow-400"
                      : line.startsWith("+")
                        ? "text-green-400"
                        : line.startsWith("-")
                          ? "text-red-400"
                          : "text-gray-200"
                }
              >
                {line}
              </span>
            ) : (
              <span className="text-transparent select-none">​</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
