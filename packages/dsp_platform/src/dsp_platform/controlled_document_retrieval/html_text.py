"""Minimal HTML-to-text extraction. No scraper framework."""

from __future__ import annotations

from html.parser import HTMLParser

__all__ = ["html_to_visible_text"]

_SKIP = frozenset({"script", "style", "noscript", "template"})


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag.lower() in _SKIP:
            self._skip += 1
        elif tag.lower() in {"p", "br", "div", "li", "tr", "h1", "h2", "h3"}:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in _SKIP and self._skip:
            self._skip -= 1
        elif tag.lower() in {"p", "div", "li", "tr", "h1", "h2", "h3"}:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        text = " ".join(data.split())
        if text:
            self._chunks.append(text)

    def text(self) -> str:
        joined = " ".join(part.strip() for part in self._chunks if part.strip())
        return " ".join(joined.split())


def html_to_visible_text(raw: str) -> str:
    """Return visible text. Scripts/styles are dropped."""
    parser = _VisibleTextParser()
    parser.feed(raw)
    parser.close()
    return parser.text()
