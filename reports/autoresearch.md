# Due Diligence Report

**Repository:** https://github.com/karpathy/autoresearch

> **Young Project (61 days old).** Maturity signals (CI, dev dependencies, contributor diversity, PR throughput) were weighted lower than for an established repo, since these are naturally weak early on. Scores below 180-day age threshold should be read with that context.

- **Stars:** 79,326
- **Forks:** 11,581
- **License:** —
- **Primary language:** Python
- **Default branch:** master
- **Last push:** 2026-03-26T00:07:37Z
- **Age:** 61 days

## Recommendation: ADOPT WITH CAUTION

**Overall score: 5.2/10**

This 61-day-old research project scores 5.2/10 overall with reasonable code quality and zero security issues, but suffers from critical sustainability risks: single maintainer (karpathy, 78% of commits), no testing infrastructure, and a 1% PR merge ratio despite 100 open PRs. Suitable only for experimental/research use with low production expectations.

## Score breakdown

| Dimension | Score |
|---|---|
| Repo structure | 4.0/10  `####------` |
| Dependencies | 5.0/10  `#####-----` |
| Security | 7.0/10  `#######---` |
| Documentation | 5.0/10  `#####-----` |
| Contributor activity | 5.0/10  `#####-----` |
| Issue health | 5.0/10  `#####-----` |
|---|---|
| **Code team avg** | 5.3/10  `#####-----` |
| **Business team avg** | 5.0/10  `#####-----` |

## Strengths

- Clean security posture with no detected secrets or sensitive files exposed.
- Focused dependency set (9 runtime deps) appropriate for ML/data science workflows.
- Fast issue resolution (0.1 day median close time) shows active triage.
- Reasonable code structure for early-stage research with clear README overview.
- Recent activity within 42 days indicates ongoing development.

## Risks

- Bus factor of 1: karpathy responsible for 78% of commits (28/36) with minimal secondary contributors.
- No testing infrastructure, CI/CD pipelines, or dev dependencies despite pyproject.toml presence.
- Severe PR integration problem: only 1% merge ratio (1 of 100 closed PRs) with 100 open PRs suggests contributions are rejected or stalled.
- Inconsistent dependency version pinning (torch ==2.9.1 vs numpy >=) creates reproducibility concerns.
- Missing critical documentation: no installation instructions, usage examples, CONTRIBUTING, or CODE_OF_CONDUCT.

## Code team findings

The 3,600 LOC codebase lacks any test suite or CI configuration, indicating exploratory research-stage maturity. Dependency hygiene is mixed with loose version specs and no dev/lint tools. No security red flags detected.

## Business team findings

Single-maintainer dependency (karpathy 78% of commits) creates severe sustainability risk. Despite fast issue closure, the 1% PR merge ratio and 100 open PRs suggest contributions are not being integrated, signaling potential project stagnation or selective acceptance policies.
