import { useEffect, useState } from "react";
import { InputScreen } from "./components/InputScreen";
import { ProgressView } from "./components/ProgressView";
import { ReportView } from "./components/ReportView";
import { useAnalysis } from "./hooks/useAnalysis";

export default function App() {
  const [submittedUrl, setSubmittedUrl] = useState<string | null>(null);
  const { state, reset } = useAnalysis(submittedUrl);

  useEffect(() => {
    const slug = submittedUrl?.split("github.com/").pop()?.replace(/\/$/, "");
    if (state.view === "report" && state.recommendation) {
      document.title = `${state.recommendation} — ${slug ?? "Due Diligence"}`;
    } else if (state.view === "progress" && slug) {
      document.title = `Analyzing ${slug} — Due Diligence`;
    } else if (state.view === "error") {
      document.title = "Error — Due Diligence";
    } else {
      document.title = "Tech Due Diligence";
    }
  }, [state.view, state.recommendation, submittedUrl]);

  const handleNew = () => {
    setSubmittedUrl(null);
    reset();
  };

  if (state.view === "error") {
    return (
      <div className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6">
        <div className="font-mono text-xs uppercase tracking-widest text-accent-bad">
          analysis failed
        </div>
        <h1 className="mt-2 text-2xl text-zinc-100">Something went wrong.</h1>
        <pre className="mt-4 overflow-auto rounded-md border border-zinc-800 bg-zinc-900 p-3 font-mono text-xs text-zinc-300">
          {state.error}
        </pre>
        <button
          type="button"
          onClick={handleNew}
          className="mt-6 self-start rounded bg-zinc-100 px-3 py-1.5 font-mono text-xs uppercase tracking-wider text-zinc-950 hover:bg-white"
        >
          back
        </button>
      </div>
    );
  }

  if (state.view === "report") {
    return <ReportView state={state} onReset={handleNew} />;
  }

  if (state.view === "progress" && submittedUrl) {
    return <ProgressView state={state} onCancel={handleNew} />;
  }

  // Brief gap between POST /analyze and first SSE event — show transitional state
  if (submittedUrl && state.view === "input") {
    return (
      <div className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6">
        <div className="font-mono text-xs uppercase tracking-widest text-zinc-500">
          starting
        </div>
        <h1 className="mt-1 break-all font-mono text-base text-zinc-100">
          {submittedUrl}
        </h1>
        <div className="mt-4 font-mono text-xs text-zinc-500">
          contacting backend<span className="animate-pulse-slow">…</span>
        </div>
      </div>
    );
  }

  return <InputScreen onSubmit={setSubmittedUrl} />;
}
