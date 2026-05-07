export type Team = "code" | "business";

export type AgentEvent =
  | { type: "node_start"; node: string; team?: Team }
  | { type: "node_complete"; node: string; team?: Team; summary: string }
  | {
      type: "team_complete";
      team: Team;
      scores: Record<string, number>;
      overall_score: number;
    }
  | { type: "report_ready"; report: Report }
  | { type: "complete"; usage: Usage }
  | { type: "error"; message: string };

export type Recommendation = "ADOPT" | "ADOPT WITH CAUTION" | "AVOID";

export type Veto = {
  dimension: string;
  score: number;
  verdict_cap: string;
} | null;

export type Report = {
  recommendation: Recommendation;
  report_markdown: string;
  overall_score: number;
  veto: Veto;
};

export type Usage = {
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
};

export type AgentStatus = "pending" | "running" | "complete";

export type SpecialistState = {
  status: AgentStatus;
  summary: string | null;
};

export const CODE_SPECIALISTS = [
  "repo_analyzer",
  "dependency_auditor",
  "security_scanner",
] as const;

export const BUSINESS_SPECIALISTS = [
  "readme_analyzer",
  "contributor_activity",
  "issue_health",
] as const;

export const TOP_PIPELINE = [
  "fetch_metadata",
  "clone_repo",
  "code_team",
  "business_team",
  "report_writer",
] as const;

export const SPECIALIST_LABELS: Record<string, string> = {
  repo_analyzer: "Repo Analyzer",
  dependency_auditor: "Dependency Auditor",
  security_scanner: "Security Scanner",
  readme_analyzer: "README / Docs",
  contributor_activity: "Contributor Activity",
  issue_health: "Issue Health",
  fetch_metadata: "Fetch metadata",
  clone_repo: "Clone repository",
  code_team: "Code team",
  business_team: "Business team",
  report_writer: "Report writer",
};
