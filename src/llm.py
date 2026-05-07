"""Shared LLM factory + run-scoped token / cost tracking.

Default model is Haiku 4.5; pass ``model=`` to override on a per-node basis.
Every ``ChatAnthropic`` returned from ``get_llm`` has a usage callback wired in
so token counts and cost accumulate to a module-level total which can be
printed at the end of a run via ``print_usage_summary()``.
"""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Per-million-token prices in USD. Sources: Anthropic public pricing.
# Cache prices are: cache_read = 0.1x base input, cache_create = 1.25x base input.
MODEL_PRICING: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {
        "input": 1.00,
        "output": 5.00,
        "cache_read": 0.10,
        "cache_create": 1.25,
    },
    "claude-sonnet-4-6": {
        "input": 3.00,
        "output": 15.00,
        "cache_read": 0.30,
        "cache_create": 3.75,
    },
}
_FALLBACK_PRICING = MODEL_PRICING["claude-haiku-4-5-20251001"]


class AnthropicAuthError(RuntimeError):
    """Raised when ANTHROPIC_API_KEY is missing."""


@dataclass
class _RunTotal:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_create_tokens: int = 0
    cost_usd: float = 0.0
    by_model: dict[str, dict[str, float]] = field(default_factory=dict)


_total = _RunTotal()
_lock = threading.Lock()


def _check_key() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY", "").strip():
        raise AnthropicAuthError(
            "ANTHROPIC_API_KEY is not set. Add it to your .env file (see "
            ".env.example) or export it. Get a key at "
            "https://console.anthropic.com/settings/keys."
        )


def _price(model: str, inp: int, out: int, cr: int, cc: int) -> float:
    rates = MODEL_PRICING.get(model, _FALLBACK_PRICING)
    return (
        inp * rates["input"]
        + out * rates["output"]
        + cr * rates["cache_read"]
        + cc * rates["cache_create"]
    ) / 1_000_000


class _UsageLogger(BaseCallbackHandler):
    """Per-call usage logger; accumulates into the module-level _total."""

    def __init__(self, model: str) -> None:
        self.model = model

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        for gens in response.generations:
            for gen in gens:
                msg = getattr(gen, "message", None)
                meta: dict[str, Any] = getattr(msg, "usage_metadata", None) or {}
                if not meta:
                    continue
                inp = int(meta.get("input_tokens", 0) or 0)
                out = int(meta.get("output_tokens", 0) or 0)
                details = meta.get("input_token_details", {}) or {}
                cr = int(details.get("cache_read", 0) or 0)
                cc = int(details.get("cache_creation", 0) or 0)
                cost = _price(self.model, inp, out, cr, cc)

                with _lock:
                    _total.calls += 1
                    _total.input_tokens += inp
                    _total.output_tokens += out
                    _total.cache_read_tokens += cr
                    _total.cache_create_tokens += cc
                    _total.cost_usd += cost
                    bucket = _total.by_model.setdefault(
                        self.model,
                        {"calls": 0, "input": 0, "output": 0, "cache_read": 0, "cache_create": 0, "cost": 0.0},
                    )
                    bucket["calls"] += 1
                    bucket["input"] += inp
                    bucket["output"] += out
                    bucket["cache_read"] += cr
                    bucket["cache_create"] += cc
                    bucket["cost"] += cost

                logger.info(
                    "[llm] model=%s in=%d out=%d cache_r=%d cache_w=%d cost=$%.4f",
                    self.model,
                    inp,
                    out,
                    cr,
                    cc,
                    cost,
                )


@lru_cache(maxsize=8)
def get_llm(
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 2048,
) -> ChatAnthropic:
    """Return a cached ChatAnthropic with usage tracking attached."""
    _check_key()
    return ChatAnthropic(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=60,
        callbacks=[_UsageLogger(model)],
    )


def reset_usage() -> None:
    """Reset the global counter — call at the start of each run."""
    global _total
    with _lock:
        _total = _RunTotal()


def get_usage() -> _RunTotal:
    """Snapshot of the current run's usage."""
    return _total


def print_usage_summary(prefix: str = "") -> None:
    print(f"\n{prefix}=== LLM usage summary ===")
    print(f"  total calls:         {_total.calls}")
    print(f"  input tokens:        {_total.input_tokens:,}")
    print(f"  output tokens:       {_total.output_tokens:,}")
    if _total.cache_read_tokens or _total.cache_create_tokens:
        print(f"  cache read tokens:   {_total.cache_read_tokens:,}")
        print(f"  cache write tokens:  {_total.cache_create_tokens:,}")
    print(f"  total cost:          ${_total.cost_usd:.4f}")
    if len(_total.by_model) > 1:
        print("  by model:")
        for model, b in _total.by_model.items():
            print(
                f"    {model}: {b['calls']} calls, "
                f"in={int(b['input']):,} out={int(b['output']):,} "
                f"cost=${b['cost']:.4f}"
            )
