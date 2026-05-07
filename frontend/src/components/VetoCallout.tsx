import { Veto } from "../types/events";

type Props = {
  veto: NonNullable<Veto>;
};

export function VetoCallout({ veto }: Props) {
  const rule =
    veto.score <= 2
      ? "any single dimension at or below 2/10 forces AVOID"
      : "any single dimension at or below 3/10 caps the verdict at ADOPT WITH CAUTION";
  return (
    <aside
      role="note"
      className="my-6 rounded-md border-l-4 border-accent-bad bg-accent-bad/[0.07] py-3 pl-4 pr-5"
    >
      <div className="flex items-start gap-3">
        <span aria-hidden className="mt-0.5 text-base leading-none">
          ⚠️
        </span>
        <div className="flex-1">
          <div className="font-mono text-xs uppercase tracking-widest text-accent-bad">
            veto triggered
          </div>
          <p className="mt-1.5 text-sm leading-relaxed text-zinc-200">
            This repository scored{" "}
            <strong className="text-accent-bad">{veto.score}/10</strong> on{" "}
            <strong className="text-zinc-100">{veto.dimension}</strong>. Per
            policy, {rule}, regardless of how strong the other dimensions are.
            Strong scores elsewhere do not compensate for a single failing one.
          </p>
        </div>
      </div>
    </aside>
  );
}
