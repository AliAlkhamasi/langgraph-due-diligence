import { formatAgeDays, formatLastPush, parseDays } from "../utils/format";

export type MetaItem = { label: string; value: string };

type Props = {
  items: MetaItem[];
};

function formatValue(label: string, value: string): string {
  if (value === "—" || !value) return "—";
  if (label === "Last push") return formatLastPush(value);
  if (label === "Age") {
    const days = parseDays(value);
    return days !== null ? formatAgeDays(days) : value;
  }
  return value;
}

export function MetaGrid({ items }: Props) {
  if (items.length === 0) return null;
  return (
    <dl className="my-5 grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-3 md:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            {item.label}
          </dt>
          <dd className="mt-0.5 truncate font-mono text-sm text-zinc-200" title={formatValue(item.label, item.value)}>
            {formatValue(item.label, item.value)}
          </dd>
        </div>
      ))}
    </dl>
  );
}

type YoungBannerProps = {
  ageDays: number;
};

export function YoungBanner({ ageDays }: YoungBannerProps) {
  return (
    <aside
      role="note"
      className="my-4 rounded-md border-l-4 border-accent-info bg-accent-info/[0.07] py-2.5 pl-4 pr-5"
    >
      <div className="flex items-start gap-3">
        <span aria-hidden className="mt-0.5 text-sm leading-none text-accent-info">
          ⓘ
        </span>
        <div className="text-sm leading-relaxed text-zinc-200">
          <span className="font-semibold text-zinc-100">
            Young Project ({ageDays} days old).
          </span>{" "}
          Maturity signals (CI, dev dependencies, contributor diversity, PR
          throughput) were weighted lower than for an established repo —
          they're naturally weak this early.
        </div>
      </div>
    </aside>
  );
}
