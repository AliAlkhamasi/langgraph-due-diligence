# Due Diligence Report

**Repository:** https://github.com/pallets/flask

- **Stars:** 71,494
- **Forks:** 16,832
- **License:** BSD-3-Clause
- **Primary language:** Python
- **Default branch:** main
- **Last push:** 2026-05-02T13:14:04Z
- **Age:** 5874 days

## Recommendation: ADOPT

**Overall score: 7.8/10**

Flask is a mature, well-maintained web framework with strong code quality (9/10), excellent documentation, and zero security issues. However, critical bus factor of 1 (davidism responsible for 89% of commits) creates significant sustainability risk. The project's age (16 years), active maintenance, and professional infrastructure support adoption despite maintainer concentration concerns.

## Score breakdown

| Dimension | Score |
|---|---|
| Repo structure | 9.0/10  `#########-` |
| Dependencies | 7.0/10  `#######---` |
| Security | 8.0/10  `########--` |
| Documentation | 9.0/10  `#########-` |
| Contributor activity | 5.0/10  `#####-----` |
| Issue health | 9.0/10  `#########-` |
|---|---|
| **Code team avg** | 8.0/10  `########--` |
| **Business team avg** | 7.7/10  `########--` |

## Strengths

- Exemplary code maturity with 36K LOC, comprehensive CI/CD (5 workflows), and professional structure (src/ layout, pyproject.toml)
- Zero open issues and zero stale issues with median close time of 0 days demonstrates exceptional maintenance responsiveness
- Extensive documentation: 82 ReadTheDocs files, 79 .rst files, and clear quick-start examples
- Well-curated dependency set (29 total) with most runtime dependencies pinned to specific versions (werkzeug>=3.1.0, jinja2>=3.1.2)
- 16-year repository age with commit activity 4 days ago confirms active, sustained development

## Risks

- Bus factor of 1: davidism responsible for 89% of commits (111/124) with only 1 active contributor meeting >=3 commits/year threshold
- Maintainer concentration creates severe sustainability risk if primary contributor becomes unavailable
- Some dependencies lack version constraints (asgiref, cryptography, mypy, pyright, pytest) increasing compatibility risk
- Redundant type-checking tools (mypy and pyright) suggest potential tooling inefficiency

## Code team findings

Flask exhibits professional-grade code discipline with comprehensive testing infrastructure, modern Python tooling, and robust CI/CD pipelines. Dependency hygiene is solid with pinned versions for critical packages, though some unconstrained dependencies and redundant type-checkers present minor concerns.

## Business team findings

Documentation is exemplary with professional ReadTheDocs hosting and extensive inline docs. Issue/PR responsiveness is exceptional (zero stale issues, 0-day median close). However, critical bus factor of 1 (89% commits from single maintainer) represents a significant long-term sustainability risk despite current active maintenance.
