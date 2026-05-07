import { useEffect, useReducer } from "react";
import {
  AgentEvent,
  AgentStatus,
  BUSINESS_SPECIALISTS,
  CODE_SPECIALISTS,
  Recommendation,
  Report,
  SpecialistState,
  Team,
  TOP_PIPELINE,
  Usage,
  Veto,
} from "../types/events";

type TeamScores = {
  scores: Record<string, number>;
  overallScore: number;
};

export type AnalysisState = {
  view: "input" | "progress" | "report" | "error";
  analysisId: string | null;
  repoUrl: string | null;
  topNodes: Record<string, AgentStatus>;
  codeSpecialists: Record<string, SpecialistState>;
  businessSpecialists: Record<string, SpecialistState>;
  metadataSummary: string | null;
  cloneSummary: string | null;
  codeTeam: TeamScores | null;
  businessTeam: TeamScores | null;
  report: Report | null;
  recommendation: Recommendation | null;
  veto: Veto;
  usage: Usage | null;
  error: string | null;
};

type Action =
  | { type: "reset" }
  | { type: "started"; analysisId: string; repoUrl: string }
  | { type: "event"; event: AgentEvent }
  | { type: "fatal"; message: string };

const blankSpecialists = (names: readonly string[]): Record<string, SpecialistState> =>
  Object.fromEntries(names.map((n) => [n, { status: "pending" as AgentStatus, summary: null }]));

const blankTopNodes = (): Record<string, AgentStatus> =>
  Object.fromEntries(TOP_PIPELINE.map((n) => [n, "pending" as AgentStatus]));

export const initialState: AnalysisState = {
  view: "input",
  analysisId: null,
  repoUrl: null,
  topNodes: blankTopNodes(),
  codeSpecialists: blankSpecialists(CODE_SPECIALISTS),
  businessSpecialists: blankSpecialists(BUSINESS_SPECIALISTS),
  metadataSummary: null,
  cloneSummary: null,
  codeTeam: null,
  businessTeam: null,
  report: null,
  recommendation: null,
  veto: null,
  usage: null,
  error: null,
};

function setTopStatus(state: AnalysisState, node: string, status: AgentStatus): AnalysisState {
  if (!(node in state.topNodes)) return state;
  return { ...state, topNodes: { ...state.topNodes, [node]: status } };
}

function setSpecialist(
  state: AnalysisState,
  team: Team,
  node: string,
  patch: Partial<SpecialistState>,
): AnalysisState {
  const key = team === "code" ? "codeSpecialists" : "businessSpecialists";
  const current = state[key][node];
  if (!current) return state;
  return {
    ...state,
    [key]: { ...state[key], [node]: { ...current, ...patch } },
  };
}

function reducer(state: AnalysisState, action: Action): AnalysisState {
  switch (action.type) {
    case "reset":
      return { ...initialState };
    case "started":
      return {
        ...initialState,
        view: "progress",
        analysisId: action.analysisId,
        repoUrl: action.repoUrl,
      };
    case "fatal":
      return { ...state, view: "error", error: action.message };
    case "event": {
      const ev = action.event;
      switch (ev.type) {
        case "node_start": {
          if (ev.team && ev.node in (ev.team === "code" ? state.codeSpecialists : state.businessSpecialists)) {
            return setSpecialist(state, ev.team, ev.node, { status: "running" });
          }
          return setTopStatus(state, ev.node, "running");
        }
        case "node_complete": {
          if (ev.team) {
            return setSpecialist(state, ev.team, ev.node, {
              status: "complete",
              summary: ev.summary,
            });
          }
          let next = setTopStatus(state, ev.node, "complete");
          if (ev.node === "fetch_metadata") next = { ...next, metadataSummary: ev.summary };
          if (ev.node === "clone_repo") next = { ...next, cloneSummary: ev.summary };
          return next;
        }
        case "team_complete": {
          const teamData: TeamScores = {
            scores: ev.scores ?? {},
            overallScore: ev.overall_score,
          };
          if (ev.team === "code") {
            return { ...setTopStatus(state, "code_team", "complete"), codeTeam: teamData };
          }
          return { ...setTopStatus(state, "business_team", "complete"), businessTeam: teamData };
        }
        case "report_ready": {
          return {
            ...setTopStatus(state, "report_writer", "complete"),
            report: ev.report,
            recommendation: ev.report.recommendation,
            veto: ev.report.veto,
            view: "report",
          };
        }
        case "complete":
          return { ...state, usage: ev.usage };
        case "error":
          return { ...state, view: "error", error: ev.message };
      }
    }
  }
}

export function useAnalysis(repoUrl: string | null): {
  state: AnalysisState;
  reset: () => void;
} {
  const [state, dispatch] = useReducer(reducer, initialState);

  useEffect(() => {
    if (!repoUrl) return;

    const controller = new AbortController();
    let eventSource: EventSource | null = null;
    let terminalSeen = false;

    (async () => {
      try {
        const res = await fetch("/analyze", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ repo_url: repoUrl }),
          signal: controller.signal,
        });
        if (!res.ok) throw new Error(`POST /analyze failed: ${res.status}`);
        const { analysis_id } = (await res.json()) as { analysis_id: string };
        if (controller.signal.aborted) return;

        dispatch({ type: "started", analysisId: analysis_id, repoUrl });

        eventSource = new EventSource(`/analyze/${analysis_id}/stream`);
        eventSource.onmessage = (e) => {
          try {
            const event = JSON.parse(e.data) as AgentEvent;
            dispatch({ type: "event", event });
            if (event.type === "complete" || event.type === "error") {
              terminalSeen = true;
              eventSource?.close();
            }
          } catch (err) {
            console.error("bad event:", e.data, err);
          }
        };
        eventSource.onerror = () => {
          if (!terminalSeen) {
            dispatch({
              type: "event",
              event: { type: "error", message: "Connection to backend lost" },
            });
          }
          eventSource?.close();
        };
      } catch (err) {
        if (!controller.signal.aborted) {
          dispatch({ type: "fatal", message: String(err) });
        }
      }
    })();

    return () => {
      controller.abort();
      eventSource?.close();
    };
  }, [repoUrl]);

  return {
    state,
    reset: () => dispatch({ type: "reset" }),
  };
}
