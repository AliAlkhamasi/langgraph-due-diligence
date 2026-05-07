"""GitHub REST API client.

Single entry point: ``github_get(endpoint)`` — performs a cached GET, decodes
JSON, logs rate-limit headers, and warns when the remaining quota gets low.
Convenience wrappers (``get_repo``, ``get_contributors``, ...) build on top.

Token is read lazily from ``GITHUB_TOKEN``. ``.env`` is loaded automatically if
``python-dotenv`` is available, so callers don't need to import it.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional
from urllib.parse import urlencode

import requests
from diskcache import Cache

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"
CACHE_DIR = ".cache/github"
DEFAULT_TTL = 3600
RATE_LIMIT_WARN_THRESHOLD = 100

_CACHE_MISS = object()
_cache: Optional[Cache] = None
_session: Optional[requests.Session] = None


class GitHubAuthError(RuntimeError):
    """Raised when GITHUB_TOKEN is missing or rejected."""


def _get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise GitHubAuthError(
            "GITHUB_TOKEN is not set. Add it to your .env file (see .env.example) "
            "or export it in your shell. Generate one at "
            "https://github.com/settings/tokens (scope: public_repo)."
        )
    return token


def _get_cache() -> Cache:
    global _cache
    if _cache is None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        _cache = Cache(CACHE_DIR)
    return _cache


def _get_session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update(
            {
                "Authorization": f"Bearer {_get_token()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "tech-due-diligence/0.1",
            }
        )
        _session = s
    return _session


def _log_rate_limit(response: requests.Response) -> None:
    remaining = response.headers.get("X-RateLimit-Remaining")
    limit = response.headers.get("X-RateLimit-Limit", "?")
    if remaining is None:
        return
    try:
        n = int(remaining)
    except ValueError:
        return
    if n < RATE_LIMIT_WARN_THRESHOLD:
        logger.warning("GitHub rate limit low: %s/%s remaining", n, limit)
    else:
        logger.debug("GitHub rate limit: %s/%s remaining", n, limit)


def verify_token() -> dict:
    """Hit ``/user`` to confirm the token is valid. Returns the user payload.

    Use at startup so a bad token fails loud instead of mid-run.
    """
    session = _get_session()
    response = session.get(f"{GITHUB_API_BASE}/user", timeout=15)
    _log_rate_limit(response)
    if response.status_code == 401:
        raise GitHubAuthError(
            "GITHUB_TOKEN was rejected by GitHub (401). The token may be "
            "expired, revoked, or lacking required scopes."
        )
    response.raise_for_status()
    return response.json()


def github_get(
    endpoint: str,
    *,
    ttl: int = DEFAULT_TTL,
    params: dict | None = None,
) -> Any:
    """GET a GitHub API endpoint, cached on disk for ``ttl`` seconds.

    - ``endpoint``: path like ``/repos/pallets/flask`` or a full URL.
    - ``ttl=0`` bypasses the cache entirely.
    - Returns parsed JSON, or ``None`` for 404. Other non-2xx raise.
    """
    if endpoint.startswith("http"):
        url = endpoint
    else:
        url = f"{GITHUB_API_BASE}{endpoint if endpoint.startswith('/') else '/' + endpoint}"

    if params:
        cache_key = f"{url}?{urlencode(sorted(params.items()))}"
    else:
        cache_key = url

    cache = _get_cache()
    if ttl > 0:
        hit = cache.get(cache_key, default=_CACHE_MISS)
        if hit is not _CACHE_MISS:
            logger.debug("cache hit: %s", cache_key)
            return hit

    session = _get_session()
    response = session.get(url, params=params, timeout=30)
    _log_rate_limit(response)

    if response.status_code == 404:
        if ttl > 0:
            cache.set(cache_key, None, expire=ttl)
        return None
    if response.status_code == 401:
        raise GitHubAuthError(
            "GITHUB_TOKEN was rejected by GitHub (401) while requesting "
            f"{url}. Check token validity and scopes."
        )
    response.raise_for_status()

    data = response.json()
    if ttl > 0:
        cache.set(cache_key, data, expire=ttl)
    return data


def github_get_paginated(
    endpoint: str,
    *,
    params: dict | None = None,
    max_pages: int = 5,
    ttl: int = DEFAULT_TTL,
) -> list:
    """Page through a list endpoint. Stops when a short page is returned or
    ``max_pages`` is reached. Each page is cached individually via ``github_get``.
    """
    results: list = []
    base = dict(params or {})
    per_page = int(base.get("per_page", 30))
    for page in range(1, max_pages + 1):
        page_params = dict(base)
        page_params["page"] = page
        data = github_get(endpoint, ttl=ttl, params=page_params)
        if data is None:
            break
        if not isinstance(data, list):
            return data
        results.extend(data)
        if len(data) < per_page:
            break
    return results


def parse_repo_url(url: str) -> tuple[str, str]:
    """Parse 'https://github.com/owner/repo' (with optional .git/trailing slash)."""
    import re

    m = re.match(
        r"^(?:https?://)?(?:www\.)?github\.com/([^/\s]+)/([^/\s#?]+?)(?:\.git)?/?$",
        url.strip(),
    )
    if not m:
        raise ValueError(f"Not a valid GitHub repo URL: {url!r}")
    return m.group(1), m.group(2)


def get_repo(owner: str, repo: str) -> dict | None:
    return github_get(f"/repos/{owner}/{repo}")


def get_languages(owner: str, repo: str) -> dict | None:
    return github_get(f"/repos/{owner}/{repo}/languages")


def get_readme(owner: str, repo: str) -> dict | None:
    return github_get(f"/repos/{owner}/{repo}/readme")


def get_contributors(owner: str, repo: str, *, per_page: int = 100) -> list | None:
    return github_get(
        f"/repos/{owner}/{repo}/contributors", params={"per_page": per_page}
    )


def get_commits(
    owner: str,
    repo: str,
    *,
    since: str | None = None,
    per_page: int = 100,
) -> list | None:
    params: dict[str, Any] = {"per_page": per_page}
    if since:
        params["since"] = since
    return github_get(f"/repos/{owner}/{repo}/commits", params=params)


def get_issues(
    owner: str,
    repo: str,
    *,
    state: str = "all",
    per_page: int = 100,
) -> list | None:
    return github_get(
        f"/repos/{owner}/{repo}/issues",
        params={"state": state, "per_page": per_page},
    )


def get_pulls(
    owner: str,
    repo: str,
    *,
    state: str = "all",
    per_page: int = 100,
) -> list | None:
    return github_get(
        f"/repos/{owner}/{repo}/pulls",
        params={"state": state, "per_page": per_page},
    )


def get_branch_protection(owner: str, repo: str, branch: str = "main") -> dict | None:
    """Branch protection details, or None when not visible.

    GitHub returns 403/404 on this endpoint unless the token has admin scope on
    the repo. We treat both as "unknown" rather than letting the HTTP error
    propagate, since they have the same practical meaning for our analysis.
    """
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/branches/{branch}/protection"
    response = _get_session().get(url, timeout=30)
    _log_rate_limit(response)
    if response.status_code in (403, 404):
        return None
    response.raise_for_status()
    return response.json()
