# Due Diligence Report

**Repository:** https://github.com/requests/requests-oauthlib

- **Stars:** 1,771
- **Forks:** 426
- **License:** ISC
- **Primary language:** Python
- **Default branch:** master
- **Last push:** 2025-06-18T06:42:02Z
- **Age:** 4912 days

## Recommendation: AVOID

**Overall score: 6.0/10**

Despite solid code quality and documentation, this library exhibits critical maintenance red flags that trigger a mandatory AVOID verdict. Issue health is severely degraded with 102 stale issues (90+ days old) and a median closure time of 107 days, combined with a bus factor of 1 and only 4 commits in the past year from a single maintainer. These structural problems outweigh the codebase's technical strengths and create unacceptable adoption risk.

## Veto Triggered

This repository scored **2/10** on **Issue health**. Per policy, any single dimension at or below 2/10 forces AVOID, regardless of how strong the other dimensions are.

## Score breakdown

| Dimension | Score |
|---|---|
| Repo structure | 8.0/10  `########--` |
| Dependencies | 6.0/10  `######----` |
| Security | 7.0/10  `#######---` |
| Documentation | 8.0/10  `########--` |
| Contributor activity | 5.0/10  `#####-----` |
| Issue health | 2.0/10  `##--------` |
|---|---|
| **Code team avg** | 7.0/10  `#######---` |
| **Business team avg** | 5.0/10  `#####-----` |

## Strengths

- Well-organized codebase (~5.8K LOC) with comprehensive test coverage and dual CI workflows.
- Minimal, well-pinned runtime dependencies (oauthlib, requests) with no bloat.
- Professional documentation on ReadTheDocs with 24 supporting docs files and clear usage examples.
- Established release practices and proper Python packaging setup (setup.py, setup.cfg).

## Risks

- Bus factor of 1: single active contributor (JonathanHuot) with last commit 322 days ago creates critical continuity risk.
- Massive stale issue backlog: all 102 open issues unresolved for 90+ days with 107-day median closure time signals project neglect.
- 23 open PRs combined with stagnant issue resolution suggests maintainer capacity is overwhelmed or abandoned.
- Suspected private key in test file (tests/test_oauth1_session.py, line 22) requires verification despite appearing to be a fixture.

## Code team findings

Codebase demonstrates solid fundamentals with comprehensive testing, clear architecture, and proper packaging. However, the complete absence of specified dev/test/lint dependencies suggests underdeveloped tooling practices. A suspected RSA private key header in test fixtures requires verification.

## Business team findings

Documentation is professional and complete, but maintenance has stalled critically. Single maintainer with 4 commits/year, 102 stale issues (90+ days), and 107-day median closure time indicate the project is effectively unmaintained. This creates unacceptable risk for production adoption despite historical quality.
