"""OpenAI / ChatGPT provider package.

Research port: ``llm_adapters.openai.research_agent``.
Copilot chat adapter remains ``llm_adapters.openai_adapter``.
"""

from __future__ import annotations

from llm_adapters.openai.research_agent import ChatGptLiveResearchAgent

__all__ = ["ChatGptLiveResearchAgent"]
