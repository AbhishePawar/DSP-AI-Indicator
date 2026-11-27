"""Bounded HTML financial document extraction."""

from html.parser import HTMLParser


class HtmlExtractionError(ValueError):
    pass


class FinancialHtmlParser(HTMLParser):
    IGNORED = {
        "script", "style", "noscript", "template",
        "iframe", "svg", "head", "nav", "footer",
    }

    BLOCKS = {
        "p", "div", "section", "article",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "li", "br", "tr", "table",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = []
        self.length = 0

    def append_text(self, text):
        self.length += len(text)

        if self.length > 2_000_000:
            raise HtmlExtractionError(
                "Extracted HTML exceeds text limit"
            )

        self.parts.append(text)

    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed",
        "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr",
    }

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)

        style = "".join(
            (attributes.get("style") or "").lower().split()
        )

        hidden = (
            "hidden" in attributes
            or (attributes.get("aria-hidden") or "").lower() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        )

        if self.ignored or tag in self.IGNORED or hidden:
            if tag not in self.VOID_ELEMENTS:
                self.ignored.append(tag)
            return

        if tag in self.BLOCKS:
            self.append_text("\n")

        if tag in {"td", "th"}:
            self.append_text(" | ")

    def handle_endtag(self, tag):
        if self.ignored:
            if tag == self.ignored[-1]:
                self.ignored.pop()
            return

        if tag in self.BLOCKS:
            self.append_text("\n")

    def handle_data(self, data):
        if not self.ignored:
            text = " ".join(data.split())

            if text:
                self.append_text(text + " ")


def extract_html_text(raw: bytes) -> str:
    if len(raw) > 5 * 1024 * 1024:
        raise HtmlExtractionError(
            "HTML exceeds input size limit"
        )

    parser = FinancialHtmlParser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    parser.close()

    text = "\n".join(
        " ".join(line.split())
        for line in "".join(parser.parts).splitlines()
        if line.strip()
    )

    if not text:
        raise HtmlExtractionError(
            "HTML contains no extractable text"
        )

    return text
