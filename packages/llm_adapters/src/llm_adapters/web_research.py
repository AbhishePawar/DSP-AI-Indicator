"""Native OpenAI source discovery.

Discovered sources are untrusted candidates until independently
retrieved and validated by the DSP research evidence pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from llm_adapters.config import load_llm_config


@dataclass(frozen=True, slots=True)
class WebResearchSource:
    url: str
    title: str


@dataclass(frozen=True, slots=True)
class WebResearchResult:
    status: str
    sources: tuple[WebResearchSource, ...] = ()
    limitation: str | None = None


class OpenAIWebResearch:

    def __init__(self, *, client=None):

        self._config = load_llm_config()
        self._client = client

    def is_configured(self) -> bool:

        return bool(self._config.openai_api_key)

    def discover(self, query: str) -> WebResearchResult:

        query = str(query or "").strip()

        if not query or len(query) > 4000:

            return WebResearchResult(
                status="unavailable",
                limitation="invalid_research_query",
            )

        if not self.is_configured():

            return WebResearchResult(
                status="unavailable",
                limitation="provider_not_configured",
            )

        payload = {
            "model": self._config.openai_model,
            "tools": [{"type": "web_search"}],
            "tool_choice": "required",
            "store": False,
            "max_output_tokens": 2000,
            "input": query,
        }

        headers = {
            "Authorization":
                f"Bearer {self._config.openai_api_key}",
            "Content-Type": "application/json",
        }

        try:

            if self._client is not None:

                response = self._client.post(
                    "https://api.openai.com/v1/responses",
                    headers=headers,
                    json=payload,
                    timeout=60.0,
                )

            else:

                with httpx.Client(
                    timeout=60.0,
                    follow_redirects=False,
                ) as client:

                    response = client.post(
                        "https://api.openai.com/v1/responses",
                        headers=headers,
                        json=payload,
                    )

            if response.status_code != 200:

                return WebResearchResult(
                    status="unavailable",
                    limitation=(
                        f"provider_http_{response.status_code}"
                    ),
                )

            data = response.json()

            return self._parse_response(data)

        except (httpx.HTTPError, ValueError, TypeError):

            return WebResearchResult(
                status="unavailable",
                limitation="research_request_failed",
            )

    @staticmethod
    def _parse_response(data) -> WebResearchResult:

        if (
            not isinstance(data, dict)
            or data.get("status") != "completed"
        ):

            return WebResearchResult(
                status="unavailable",
                limitation="incomplete_research_response",
            )

        output = data.get("output")

        if not isinstance(output, list):

            return WebResearchResult(
                status="unavailable",
                limitation="invalid_research_response",
            )

        search_completed = any(
            isinstance(item, dict)
            and item.get("type") == "web_search_call"
            and item.get("status") == "completed"
            for item in output
        )

        if not search_completed:

            return WebResearchResult(
                status="unavailable",
                limitation="web_search_not_completed",
            )

        sources = {}

        for item in output:

            if not isinstance(item, dict):
                continue

            if item.get("type") != "message":
                continue

            content_items = item.get("content", [])

            if not isinstance(content_items, list):
                continue

            for content in content_items:

                if not isinstance(content, dict):
                    continue

                annotations = content.get("annotations", [])

                if not isinstance(annotations, list):
                    continue

                for annotation in annotations:

                    if not isinstance(annotation, dict):
                        continue

                    if annotation.get("type") != "url_citation":
                        continue

                    url = annotation.get("url", "")

                    if not isinstance(url, str):
                        continue

                    if len(url) > 4096:
                        continue

                    try:

                        parsed = urlsplit(url)

                        if (
                            parsed.scheme != "https"
                            or not parsed.hostname
                            or parsed.username is not None
                            or parsed.password is not None
                            or parsed.port not in (None, 443)
                        ):
                            continue

                    except ValueError:
                        continue

                    if url not in sources:

                        title = annotation.get("title")

                        sources[url] = WebResearchSource(
                            url=url,
                            title=(
                                title[:300]
                                if isinstance(title, str)
                                else ""
                            ),
                        )

                    if len(sources) >= 20:

                        return WebResearchResult(
                            status="discovered",
                            sources=tuple(sources.values()),
                        )

        if not sources:

            return WebResearchResult(
                status="unavailable",
                limitation="no_source_citations",
            )

        return WebResearchResult(
            status="discovered",
            sources=tuple(sources.values()),
        )
