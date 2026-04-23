from __future__ import annotations

import io
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .fetch import HttpClient
from .models import SourceDocument, TableData
from .utils import normalize_space

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - optional dependency at runtime only
    PdfReader = None


NUMBER_RE = re.compile(r"\(?-?\d[\d,]*(?:\.\d+)?\)?")


def _line_to_row(line: str) -> list[str] | None:
    numbers = NUMBER_RE.findall(line)
    if not numbers:
        return None
    first_number = NUMBER_RE.search(line)
    if not first_number:
        return None
    label = normalize_space(line[: first_number.start()])
    if not label:
        return None
    return [label] + numbers[:5]


def _extract_pdf_pseudo_tables(page_text: str, source_url: str, page_index: int) -> list[TableData]:
    lines = [normalize_space(line) for line in page_text.splitlines() if normalize_space(line)]
    candidates: list[list[str]] = []
    for line in lines:
        low = line.lower()
        if not any(
            kw in low
            for kw in [
                "receivable",
                "allowance",
                "impairment",
                "expected credit loss",
                "stage 1",
                "stage 2",
                "stage 3",
                "past due",
                "opening",
                "closing",
                "write-off",
                "gross",
                "net",
            ]
        ):
            continue
        parsed = _line_to_row(line)
        if parsed:
            candidates.append(parsed)

    if len(candidates) < 3:
        return []

    max_cols = max(len(row) for row in candidates)
    columns = ["Row"] + [f"Value {idx}" for idx in range(1, max_cols)]
    padded_rows = [row + [""] * (max_cols - len(row)) for row in candidates]
    return [
        TableData(
            title=f"PDF extracted table page {page_index}",
            columns=columns,
            rows=padded_rows,
            source_url=source_url,
            location=f"page-{page_index}",
        )
    ]


def guess_document_type(url: str, content_hint: str | None = None) -> str:
    low = (url or "").lower()
    if low.endswith(".pdf") or ".pdf?" in low:
        return "pdf"
    if content_hint and "pdf" in content_hint.lower():
        return "pdf"
    return "html"


def html_tables(soup: BeautifulSoup, source_url: str) -> list[TableData]:
    parsed: list[TableData] = []
    for index, table_tag in enumerate(soup.find_all("table"), start=1):
        rows = table_tag.find_all("tr")
        matrix: list[list[str]] = []
        for row in rows:
            cells = row.find_all(["th", "td"])
            matrix.append([normalize_space(cell.get_text(" ", strip=True)) for cell in cells])
        matrix = [row for row in matrix if any(cell for cell in row)]
        if not matrix:
            continue
        columns = matrix[0]
        body = matrix[1:] if len(matrix) > 1 else []
        title = f"HTML table {index}"
        parsed.append(TableData(title=title, columns=columns, rows=body, source_url=source_url, location=f"table-{index}"))
    return parsed


def parse_html_document(url: str, html: str) -> SourceDocument:
    soup = BeautifulSoup(html, "html.parser")
    text = normalize_space(soup.get_text("\n", strip=True))
    return SourceDocument(
        url=url,
        document_type="html",
        text=text,
        tables=html_tables(soup, url),
    )


def parse_pdf_document(url: str, payload: bytes, max_pages: int = 250) -> SourceDocument:
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed. Install dependencies from requirements.txt")

    reader = PdfReader(io.BytesIO(payload))
    chunks: list[str] = []
    tables: list[TableData] = []
    for page_index, page in enumerate(reader.pages, start=1):
        if page_index > max_pages:
            break
        text = page.extract_text() or ""
        if text.strip():
            chunks.append(f"[Page {page_index}] {text}")
            tables.extend(_extract_pdf_pseudo_tables(text, url, page_index))
    merged = normalize_space("\n".join(chunks))
    return SourceDocument(url=url, document_type="pdf", text=merged, tables=tables)


def load_document(client: HttpClient, url: str, max_pdf_pages: int = 250) -> SourceDocument:
    doc_type = guess_document_type(url)
    if doc_type == "pdf":
        raw = client.get_bytes(url)
        return parse_pdf_document(url, raw, max_pages=max_pdf_pages)
    html = client.get_text(url)
    return parse_html_document(url, html)


def report_period_from_url(url: str) -> str | None:
    path = urlparse(url).path.strip("/")
    bits = path.split("/")
    year = None
    kind = None
    for bit in bits:
        if bit.isdigit() and len(bit) == 4:
            year = bit
        if bit in {"annual-report", "half-year-report", "quarterly-report", "interim-report"}:
            kind = bit
    if year and kind:
        return f"{kind} {year}"
    if year:
        return year
    return None
