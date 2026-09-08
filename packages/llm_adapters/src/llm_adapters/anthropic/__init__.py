"""Anthropic / Claude provider package.

Research port: ``llm_adapters.anthropic.research_agent``.
Copilot chat adapter remains ``llm_adapters.anthropic_adapter``.
"""

from __future__ import annotations

from llm_adapters.anthropic.research_agent import ClaudeLiveResearchAgent

__all__ = ["ClaudeLiveResearchAgent"]
