from __future__ import annotations

from functools import cache
from importlib import import_module
from pathlib import Path
from typing import Any

import yaml

from .tool_base import ProviderAdapter

TOOLS_DIR = Path(__file__).resolve().parent.parent / "tools"

# One entry per tools/<tool>.yaml and harness/adapters/<tool>.py; this order is the run and board order.
TOOLS = (
    "context",
    "nimble",
    "parallel",
    "exa",
    "brave",
    "you",
    "perplexity",
    "tinyfish",
    "firecrawl",
    "predictleads",
    "datahyena",
    "autobound",
    "seltz",
    "tavily",
    "serp",
    "linkup",
    "string",
)


@cache
def _setups() -> dict[str, tuple[ProviderAdapter, dict[str, Any]]]:
    setups: dict[str, tuple[ProviderAdapter, dict[str, Any]]] = {}
    for tool in TOOLS:
        config = yaml.safe_load((TOOLS_DIR / f"{tool}.yaml").read_text())
        setup = import_module(f"harness.adapters.{tool}").setup
        for name, spec in config["setups"].items():
            if name in setups:
                raise RuntimeError(f"duplicate provider endpoint name: {name}")
            setups[name] = (setup(name, **spec.get("settings", {})), spec)
    return setups


def all_adapters() -> dict[str, ProviderAdapter]:
    return {name: adapter for name, (adapter, _) in _setups().items()}


def list_prices() -> dict[str, float]:
    return {name: float(spec["pricing"]["list_usd"]) for name, (_, spec) in _setups().items()}


DEFAULT_ENDPOINTS = tuple(name for name, (_, spec) in _setups().items() if spec["class"] == "main")


def selected_adapters(names: list[str] | tuple[str, ...] | None = None) -> list[ProviderAdapter]:
    registry = all_adapters()
    selected = list(names or DEFAULT_ENDPOINTS)
    unknown = sorted(set(selected) - set(registry))
    if unknown:
        raise ValueError(f"unknown endpoints: {', '.join(unknown)}")
    return [registry[name] for name in selected]
