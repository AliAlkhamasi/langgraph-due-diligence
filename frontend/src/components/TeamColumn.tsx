import { AgentCard } from "./AgentCard";
import { AgentStatus, SPECIALIST_LABELS, SpecialistState } from "../types/events";

type Props = {
  title: string;
  status: AgentStatus;
  specialists: Record<string, SpecialistState>;
  order: readonly string[];
  overallScore: number | null;
};

export function TeamColumn({ title, status, specialists, order, overallScore }: Props) {
  const headerColor =
    status === "complete"
      ? "text-accent-ok border-accent-ok/40"
      : status === "running"
      ? "text-accent-info border-accent-info/40"
      : "text-zinc-500 border-zinc-800";

  return (
    <div className={`rounded-lg border bg-zinc-950/40 ${headerColor.split(" ").slice(1).join(" ")}`}>
      <div className="flex items-center justify-between border-b border-inherit px-4 py-2.5">
        <span className={`font-mono text-xs uppercase tracking-widest ${headerColor.split(" ")[0]}`}>
          {title}
        </span>
        {overallScore !== null && (
          <span className="font-mono text-xs text-zinc-300">
            avg <span className="text-zinc-100">{overallScore.toFixed(1)}/10</span>
          </span>
        )}
      </div>
      <div className="space-y-1.5 p-3">
        {order.map((node) => (
          <AgentCard
            key={node}
            label={SPECIALIST_LABELS[node] ?? node}
            status={specialists[node]?.status ?? "pending"}
            summary={specialists[node]?.summary}
          />
        ))}
      </div>
    </div>
  );
}
