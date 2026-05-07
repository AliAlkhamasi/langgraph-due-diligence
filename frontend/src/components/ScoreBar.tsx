type Props = {
  score: number;
  max?: number;
  width?: "sm" | "md";
};

function colorFor(score: number): string {
  if (score >= 7) return "bg-accent-ok";
  if (score >= 4) return "bg-accent-warn";
  return "bg-accent-bad";
}

export function ScoreBar({ score, max = 10, width = "md" }: Props) {
  const clamped = Math.max(0, Math.min(max, score));
  const pct = (clamped / max) * 100;
  const color = colorFor(score);
  const trackWidth = width === "sm" ? "w-24" : "w-40";
  return (
    <div className="flex items-center gap-3">
      <div
        className={`relative h-1.5 ${trackWidth} overflow-hidden rounded-full bg-zinc-800`}
      >
        <div
          className={`h-full ${color} transition-[width] duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="font-mono text-xs tabular-nums text-zinc-300 min-w-[3.5rem] text-right">
        {score.toFixed(1)}/10
      </span>
    </div>
  );
}
