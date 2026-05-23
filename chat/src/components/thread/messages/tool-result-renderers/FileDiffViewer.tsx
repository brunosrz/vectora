"use client";

/**
 * FileDiffViewer — renderiza diff unificado com highlighting red/green.
 *
 * Usado para `render_hint: "diff"` e `ui_component: "file_diff"`.
 * Aceita tanto a saída textual da tool file_edit quanto um objeto {diff, file_path}.
 */

interface FileDiffViewerProps {
  content: string;
  fileName?: string;
}

type LineType = "added" | "removed" | "header" | "meta" | "normal";

interface DiffLine {
  type: LineType;
  content: string;
  lineNo?: number;
}

function parseDiff(raw: string): DiffLine[] {
  return raw.split("\n").map((line): DiffLine => {
    if (line.startsWith("+++") || line.startsWith("---")) {
      return { type: "meta", content: line };
    }
    if (line.startsWith("@@")) {
      return { type: "header", content: line };
    }
    if (line.startsWith("+")) {
      return { type: "added", content: line.slice(1) };
    }
    if (line.startsWith("-")) {
      return { type: "removed", content: line.slice(1) };
    }
    return {
      type: "normal",
      content: line.startsWith(" ") ? line.slice(1) : line,
    };
  });
}

const LINE_STYLES: Record<LineType, string> = {
  added: "bg-green-50 text-green-900 border-l-2 border-green-400",
  removed:
    "bg-red-50 text-red-900 border-l-2 border-red-400 line-through opacity-70",
  header: "bg-blue-50 text-blue-700 font-mono text-xs",
  meta: "text-gray-500 font-mono text-xs",
  normal: "text-gray-800",
};

const LINE_PREFIXES: Record<LineType, string> = {
  added: "+",
  removed: "-",
  header: "",
  meta: "",
  normal: " ",
};

export function FileDiffViewer({ content, fileName }: FileDiffViewerProps) {
  const lines = parseDiff(content);
  const added = lines.filter((l) => l.type === "added").length;
  const removed = lines.filter((l) => l.type === "removed").length;

  return (
    <div className="rounded-md overflow-hidden border border-gray-200 text-sm font-mono">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-800 text-gray-100">
        <span className="text-xs truncate max-w-xs">{fileName ?? "diff"}</span>
        <div className="flex gap-2 text-xs shrink-0">
          {added > 0 && <span className="text-green-400">+{added}</span>}
          {removed > 0 && <span className="text-red-400">-{removed}</span>}
        </div>
      </div>

      {/* Diff lines */}
      <div className="overflow-x-auto max-h-[400px] overflow-y-auto bg-white">
        <table className="w-full border-collapse text-xs">
          <tbody>
            {lines.map((line, idx) => (
              <tr key={idx} className={LINE_STYLES[line.type]}>
                <td className="select-none w-6 text-center text-gray-400 border-r border-gray-200 px-1 shrink-0">
                  {LINE_PREFIXES[line.type]}
                </td>
                <td className="px-3 py-0.5 whitespace-pre break-all">
                  {line.content || " "}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
