import { Recommendation } from "../types/events";

type Props = {
  recommendation: Recommendation;
};

const STYLES: Record<Recommendation, string> = {
  ADOPT: "border-accent-ok/50 bg-accent-ok/10 text-accent-ok",
  "ADOPT WITH CAUTION": "border-accent-warn/50 bg-accent-warn/10 text-accent-warn",
  AVOID: "border-accent-bad/50 bg-accent-bad/10 text-accent-bad",
};

export function RecommendationBadge({ recommendation }: Props) {
  return (
    <span
      className={`inline-flex items-center rounded-md border px-3 py-1 font-mono text-xs uppercase tracking-widest ${STYLES[recommendation]}`}
    >
      {recommendation}
    </span>
  );
}
