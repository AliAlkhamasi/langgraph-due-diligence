import { FormEvent, useState } from "react";

const REPO_URL_REGEX = /^(https?:\/\/)?(www\.)?github\.com\/[^/\s]+\/[^/\s#?]+\/?$/i;

type Props = {
  onSubmit: (url: string) => void;
};

export function InputScreen({ onSubmit }: Props) {
  const [value, setValue] = useState("https://github.com/pallets/flask");
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const trimmed = value.trim();
    if (!REPO_URL_REGEX.test(trimmed)) {
      setError("That doesn't look like a github.com/owner/repo URL.");
      return;
    }
    setError(null);
    onSubmit(trimmed);
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6">
      <div className="mb-8">
        <div className="mb-1 font-mono text-xs uppercase tracking-widest text-zinc-500">
          tech due diligence
        </div>
        <h1 className="text-3xl font-semibold tracking-tight text-zinc-100">
          Should we adopt this library?
        </h1>
        <p className="mt-2 text-sm text-zinc-400">
          Enter a public GitHub repo and a multi-agent system will produce a structured
          adoption verdict — code quality, dependencies, security, docs, contributor
          activity, and issue health.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label
            htmlFor="repo"
            className="mb-1.5 block font-mono text-xs uppercase tracking-wider text-zinc-500"
          >
            repository url
          </label>
          <input
            id="repo"
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder="https://github.com/owner/repo"
            className="w-full rounded-md border border-zinc-800 bg-zinc-900 px-3 py-2.5 font-mono text-sm text-zinc-100 placeholder-zinc-600 transition focus:border-accent-info focus:outline-none focus:ring-1 focus:ring-accent-info"
            autoFocus
            spellCheck={false}
          />
          {error && (
            <div className="mt-2 font-mono text-xs text-accent-bad">{error}</div>
          )}
        </div>

        <button
          type="submit"
          className="w-full rounded-md bg-zinc-100 px-4 py-2.5 text-sm font-medium text-zinc-950 transition hover:bg-white"
        >
          Analyze
        </button>
      </form>

      <div className="mt-10 grid grid-cols-2 gap-2 font-mono text-[11px] text-zinc-600">
        <button
          type="button"
          className="rounded border border-zinc-800 px-2 py-1.5 text-left hover:border-zinc-700 hover:text-zinc-400"
          onClick={() => setValue("https://github.com/tiangolo/fastapi")}
        >
          tiangolo/fastapi
        </button>
        <button
          type="button"
          className="rounded border border-zinc-800 px-2 py-1.5 text-left hover:border-zinc-700 hover:text-zinc-400"
          onClick={() => setValue("https://github.com/requests/requests-oauthlib")}
        >
          requests/requests-oauthlib
        </button>
      </div>
    </div>
  );
}
