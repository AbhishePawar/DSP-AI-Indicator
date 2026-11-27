"""Resource-constrained PDF text extraction worker."""

import io
import resource
import sys

MAX_INPUT = 20 * 1024 * 1024
MAX_PAGES = 500
MAX_TEXT = 2_000_000


def main():
    resource.setrlimit(
        resource.RLIMIT_AS,
        (512 * 1024 * 1024, 512 * 1024 * 1024),
    )
    resource.setrlimit(resource.RLIMIT_CPU, (10, 12))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    from pypdf import PdfReader

    raw = sys.stdin.buffer.read(MAX_INPUT + 1)

    if len(raw) > MAX_INPUT:
        raise ValueError("PDF input exceeds size limit")

    if not raw.startswith(b"%PDF-"):
        raise ValueError("Invalid PDF signature")

    reader = PdfReader(io.BytesIO(raw), strict=True)

    if reader.is_encrypted:
        raise ValueError("Encrypted PDF is unsupported")

    if len(reader.pages) > MAX_PAGES:
        raise ValueError("PDF page limit exceeded")

    pages = []
    total = 0

    for number, page in enumerate(reader.pages, 1):
        text = page.extract_text() or ""

        if not text.strip():
            continue

        entry = f"[PDF page {number}]\n{text}"
        total += len(entry) + 2

        if total > MAX_TEXT:
            raise ValueError("PDF text limit exceeded")

        pages.append(entry)

    if not pages:
        raise ValueError("PDF contains no extractable text")

    sys.stdout.buffer.write(
        "\n\n".join(pages).encode("utf-8")
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(2)
