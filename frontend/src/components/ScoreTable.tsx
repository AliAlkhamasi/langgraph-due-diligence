import { ScoreBar } from "./ScoreBar";

type Scores = Record<string, number>;

type Props = {
  codeScores: Scores;
  codeOverall: number;
  bizScores: Scores;
  bizOverall: number;
  vetoDimension?: string | null;
};

type Row = {
  label: string;
  score: number;
  isSummary?: boolean;
};

const SCORE_KEY_FOR_LABEL: Record<string, [keyof Scores | string, "code" | "biz"]> = {
  "Repo structure": ["repo", "code"],
  Dependencies: ["dependencies", "code"],
  Security: ["security", "code"],
  Documentation: ["documentation", "biz"],
  "Contributor activity": ["contributors", "biz"],
  "Issue health": ["issues", "biz"],
};

export function ScoreTable({
  codeScores,
  codeOverall,
  bizScores,
  bizOverall,
  vetoDimension,
}: Props) {
  const rows: Row[] = Object.entries(SCORE_KEY_FOR_LABEL).map(([label, [key, team]]) => ({
    label,
    score: (team === "code" ? codeScores[key as string] : bizScores[key as string]) ?? 0,
  }));

  const summaryRows: Row[] = [
    { label: "Code team avg", score: codeOverall, isSummary: true },
    { label: "Business team avg", score: bizOverall, isSummary: true },
  ];

  return (
    <section className="my-6">
      <h2 className="mb-3 font-mono text-xs uppercase tracking-widest text-zinc-500">
        score breakdown
      </h2>
      <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/30">
        {rows.map((row, i) => {
          const isVeto = vetoDimension === row.label;
          return (
            <div
              key={row.label}
              className={`flex items-center justify-between gap-4 px-4 py-2.5 ${
                i > 0 ? "border-t border-zinc-900/70" : ""
              } ${isVeto ? "bg-accent-bad/5" : ""}`}
            >
              <div className="flex items-center gap-2 text-sm">
                <span className={isVeto ? "text-accent-bad" : "text-zinc-300"}>
                  {row.label}
                </span>
                {isVeto && (
                  <span className="rounded border border-accent-bad/40 bg-accent-bad/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-accent-bad">
                    veto
                  </span>
                )}
              </div>
              <ScoreBar score={row.score} />
            </div>
          );
        })}
        {summaryRows.map((row, i) => (
          <div
            key={row.label}
            className={`flex items-center justify-between gap-4 bg-zinc-900/40 px-4 py-2.5 ${
              i === 0 ? "border-t-2 border-zinc-800" : "border-t border-zinc-900/70"
            }`}
          >
            <span className="text-sm font-medium text-zinc-100">{row.label}</span>
            <ScoreBar score={row.score} />
          </div>
        ))}
      </div>
    </section>
  );
}
