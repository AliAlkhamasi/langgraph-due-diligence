import { AgentStatus } from "../types/events";

type Props = {
  label: string;
  status: AgentStatus;
  summary?: string | null;
};

const GLYPH: Record<AgentStatus, string> = {
  pending: "○",
  running: "◐",
  complete: "●",
};

const COLOR: Record<AgentStatus, string> = {
  pending: "text-zinc-600",
  running: "text-accent-info",
  complete: "text-accent-ok",
};

const ROW_BORDER: Record<AgentStatus, string> = {
  pending: "border-zinc-800/50",
  running: "border-accent-info/50",
  complete: "border-zinc-800",
};

export function AgentCard({ label, status, summary }: Props) {
  return (
    <div
      className={`rounded border ${ROW_BORDER[status]} bg-zinc-900/50 px-3 py-2 transition`}
    >
      <div className="flex items-center gap-2">
        <span
          className={`${COLOR[status]} font-mono text-base leading-none ${
            status === "running" ? "animate-pulse-slow" : ""
          }`}
        >
          {GLYPH[status]}
        </span>
        <span
          className={`text-sm ${
            status === "complete" ? "text-zinc-100" : status === "running" ? "text-zinc-100" : "text-zinc-500"
          }`}
        >
          {label}
        </span>
      </div>
      {status === "complete" && summary && (
        <div className="mt-1 pl-6 font-mono text-[11px] leading-relaxed text-zinc-500">
          {summary}
        </div>
      )}
      {status === "running" && (
        <div className="mt-1 pl-6 font-mono text-[11px] text-accent-info">
          working…
        </div>
      )}
    </div>
  );
}
