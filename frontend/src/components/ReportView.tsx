import { useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AnalysisState } from "../hooks/useAnalysis";
import { parseDays } from "../utils/format";
import { MetaGrid, MetaItem, YoungBanner } from "./MetaGrid";
import { RecommendationBadge } from "./RecommendationBadge";
import { ScoreTable } from "./ScoreTable";
import { VetoCallout } from "./VetoCallout";

type Props = {
  state: AnalysisState;
  onReset: () => void;
};

type Parsed = {
  metadata: MetaItem[];
  introMd: string;
  bodyMd: string;
};

function parseMarkdown(md: string): Parsed {
  let working = md;

  // Strip H1 (already hidden, but easier to drop here)
  working = working.replace(/^# .+\n+/m, "");
  // Strip "**Repository:** ..." line — duplicated by header
  working = working.replace(/^\*\*Repository:\*\*.*\n+/m, "");
  // Strip "## Recommendation: ..." line — duplicated by header badge
  working = working.replace(/^## Recommendation:.*\n+/m, "");
  // Strip "**Overall score: ...**" — duplicated by header
  working = working.replace(/^\*\*Overall score:.*\*\*\s*\n+/m, "");
  // Strip the "## Veto Triggered" section — rendered as VetoCallout
  working = working.replace(/^## Veto Triggered[\s\S]*?(?=^## |$)/m, "");
  // Strip the "## Score breakdown" section — rendered as ScoreTable
  working = working.replace(/^## Score breakdown[\s\S]*?(?=^## )/m, "");
  // Strip the Young Project blockquote — rendered as YoungBanner
  working = working.replace(/^> \*\*Young Project.*\n+/m, "");

  // Extract metadata bullet list (before any ## heading)
  const metadata: MetaItem[] = [];
  working = working.replace(/(?:^- \*\*[^*]+:\*\*\s*.*\n?)+/m, (block) => {
    block.split("\n").forEach((line) => {
      const m = line.match(/^- \*\*([^*]+):\*\*\s*(.*)$/);
      if (m) metadata.push({ label: m[1].trim(), value: m[2].trim() });
    });
    return "";
  });

  // Split remaining into intro (exec summary) and body (strengths onwards)
  const firstHeading = working.search(/^## /m);
  const introMd =
    firstHeading >= 0 ? working.slice(0, firstHeading).trim() : working.trim();
  const bodyMd = firstHeading >= 0 ? working.slice(firstHeading).trim() : "";

  return { metadata, introMd, bodyMd };
}

const PROSE_CLASSES = [
  "prose prose-invert max-w-none",
  "prose-headings:font-semibold prose-headings:tracking-tight",
  "prose-h1:hidden",
  "prose-h2:mt-8 prose-h2:mb-3 prose-h2:text-base prose-h2:font-mono prose-h2:uppercase prose-h2:tracking-widest prose-h2:text-zinc-500",
  "prose-p:text-zinc-300 prose-li:text-zinc-300",
  "prose-strong:text-zinc-100",
  "prose-code:rounded prose-code:bg-zinc-900 prose-code:px-1 prose-code:py-0.5 prose-code:font-mono prose-code:text-xs prose-code:text-zinc-300 prose-code:before:content-none prose-code:after:content-none",
].join(" ");

export function ReportView({ state, onReset }: Props) {
  if (!state.report) return null;
  const { report, usage } = state;

  const parsed = useMemo(() => parseMarkdown(report.report_markdown), [report.report_markdown]);
  const ageItem = parsed.metadata.find((m) => m.label === "Age");
  const ageDays = ageItem ? parseDays(ageItem.value) : null;
  const isYoung = ageDays !== null && ageDays < 180;

  const handleDownload = () => {
    const blob = new Blob([report.report_markdown], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const slug =
      (state.repoUrl ?? "report").split("github.com/").pop()?.replace("/", "_") ?? "report";
    a.download = `${slug}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-6 flex items-baseline justify-between gap-4">
        <div>
          <div className="font-mono text-xs uppercase tracking-widest text-zinc-500">
            verdict for
          </div>
          <h1 className="mt-1 break-all font-mono text-base text-zinc-100">
            {state.repoUrl}
          </h1>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleDownload}
            className="rounded border border-zinc-800 px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
          >
            download .md
          </button>
          <button
            type="button"
            onClick={onReset}
            className="rounded bg-zinc-100 px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-zinc-950 hover:bg-white"
          >
            new analysis
          </button>
        </div>
      </div>

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <RecommendationBadge recommendation={report.recommendation} />
        <span className="font-mono text-sm text-zinc-400">
          overall <span className="text-zinc-100">{report.overall_score}/10</span>
        </span>
        {report.veto && (
          <span className="font-mono text-xs text-accent-bad">
            veto: {report.veto.dimension} {report.veto.score}/10
          </span>
        )}
      </div>

      {isYoung && ageDays !== null && <YoungBanner ageDays={ageDays} />}

      <MetaGrid items={parsed.metadata} />

      {parsed.introMd && (
        <article className={PROSE_CLASSES}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.introMd}</ReactMarkdown>
        </article>
      )}

      {report.veto && <VetoCallout veto={report.veto} />}

      {state.codeTeam && state.businessTeam && (
        <ScoreTable
          codeScores={state.codeTeam.scores}
          codeOverall={state.codeTeam.overallScore}
          bizScores={state.businessTeam.scores}
          bizOverall={state.businessTeam.overallScore}
          vetoDimension={report.veto?.dimension ?? null}
        />
      )}

      {parsed.bodyMd && (
        <article className={PROSE_CLASSES}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{parsed.bodyMd}</ReactMarkdown>
        </article>
      )}

      {usage && (
        <div className="mt-10 border-t border-zinc-900 pt-4 font-mono text-xs text-zinc-500">
          {usage.calls} llm calls · {usage.input_tokens.toLocaleString()} in /{" "}
          {usage.output_tokens.toLocaleString()} out tokens · ${usage.cost_usd.toFixed(4)}
        </div>
      )}
    </div>
  );
}
