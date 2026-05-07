# Due Diligence Report

**Repository:** https://github.com/tiangolo/fastapi

- **Stars:** 97,951
- **Forks:** 9,209
- **License:** MIT
- **Primary language:** Python
- **Default branch:** master
- **Last push:** 2026-05-05T11:43:18Z
- **Age:** 2706 days

## Recommendation: ADOPT

**Overall score: 8.2/10**

FastAPI is a mature, well-maintained library with strong code quality (8.0/10), excellent documentation, and active development. The 8.2/10 overall score and absence of critical risks support adoption. Minor concerns around dependency version pinning and issue triage do not outweigh the substantial benefits of a production-ready framework with 2,706 days of history and 1 day since last commit.

## Score breakdown

| Dimension | Score |
|---|---|
| Repo structure | 9.0/10  `#########-` |
| Dependencies | 7.0/10  `#######---` |
| Security | 8.0/10  `########--` |
| Documentation | 10.0/10  `##########` |
| Contributor activity | 9.0/10  `#########-` |
| Issue health | 6.0/10  `######----` |
|---|---|
| **Code team avg** | 8.0/10  `########--` |
| **Business team avg** | 8.3/10  `########--` |

## Strengths

- Comprehensive test suite and 19 CI/CD workflows demonstrate professional code discipline and reliability
- Exceptional documentation with 23KB README, 1,604 doc files, and dedicated external site
- Strong maintainer activity with 1,000 commits from 64 contributors in past year and last commit 1 day ago
- No detected secrets or security red flags in filesystem scan
- Healthy bus factor of 2 with 9 active contributors reducing single-point-of-failure risk

## Risks

- 33% of open issues are stale (untouched 90+ days), indicating inconsistent issue triage despite strong PR responsiveness
- Multiple dependencies lack upper version bounds, risking breaking changes from transitive dependency updates
- Conflicting version constraints on httpx, pydantic, pydantic-settings, and pyyaml may cause resolution issues

## Code team findings

FastAPI exhibits exemplary code maturity with 377K LOC across 1,119 files, comprehensive testing infrastructure, and clear separation of concerns. Dependency hygiene is solid with 26 runtime and 39 dev dependencies, though version pinning inconsistencies and missing upper bounds present minor risks.

## Business team findings

The project demonstrates professional-grade documentation and strong maintainer engagement with 1 day since last commit. However, 33% stale issue rate and high open-to-closed issue ratio suggest maintenance gaps in issue triage, despite excellent PR merge velocity (45% ratio) and 0.8-day median close time.
