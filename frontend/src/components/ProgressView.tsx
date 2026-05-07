import { AgentCard } from "./AgentCard";
import { TeamColumn } from "./TeamColumn";
import { AnalysisState } from "../hooks/useAnalysis";
import { BUSINESS_SPECIALISTS, CODE_SPECIALISTS, SPECIALIST_LABELS } from "../types/events";

type Props = {
  state: AnalysisState;
  onCancel: () => void;
};

export function ProgressView({ state, onCancel }: Props) {
  const codeStatus = state.topNodes.code_team;
  const bizStatus = state.topNodes.business_team;

  return (
    <div className="mx-auto max-w-5xl px-6 py-12">
      <div className="mb-8 flex items-baseline justify-between">
        <div>
          <div className="font-mono text-xs uppercase tracking-widest text-zinc-500">
            analyzing
          </div>
          <h1 className="mt-1 font-mono text-lg text-zinc-100">{state.repoUrl}</h1>
        </div>
        <button
          type="button"
          onClick={onCancel}
          className="font-mono text-xs uppercase tracking-wider text-zinc-500 hover:text-zinc-300"
        >
          cancel
        </button>
      </div>

      <div className="mb-6 rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
        <div className="font-mono text-xs uppercase tracking-widest text-zinc-500">
          top supervisor
        </div>
        <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <AgentCard
            label={SPECIALIST_LABELS.fetch_metadata}
            status={state.topNodes.fetch_metadata}
            summary={state.metadataSummary}
          />
          <AgentCard
            label={SPECIALIST_LABELS.clone_repo}
            status={state.topNodes.clone_repo}
            summary={state.cloneSummary}
          />
        </div>
      </div>

      <div className="mb-1 flex items-center gap-2">
        <div className="h-px flex-1 bg-zinc-800" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          parallel teams
        </span>
        <div className="h-px flex-1 bg-zinc-800" />
      </div>

      <div className="grid grid-cols-1 gap-4 py-4 md:grid-cols-2">
        <TeamColumn
          title="code team"
          status={codeStatus}
          specialists={state.codeSpecialists}
          order={CODE_SPECIALISTS}
          overallScore={state.codeTeam?.overallScore ?? null}
        />
        <TeamColumn
          title="business team"
          status={bizStatus}
          specialists={state.businessSpecialists}
          order={BUSINESS_SPECIALISTS}
          overallScore={state.businessTeam?.overallScore ?? null}
        />
      </div>

      <div className="mb-1 mt-4 flex items-center gap-2">
        <div className="h-px flex-1 bg-zinc-800" />
        <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
          synthesis
        </span>
        <div className="h-px flex-1 bg-zinc-800" />
      </div>

      <div className="mt-4 rounded-lg border border-zinc-800 bg-zinc-950/40 p-4">
        <AgentCard
          label={SPECIALIST_LABELS.report_writer}
          status={state.topNodes.report_writer}
          summary={state.recommendation ? `verdict: ${state.recommendation}` : null}
        />
      </div>
    </div>
  );
}
