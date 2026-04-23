from __future__ import annotations

import argparse
from pathlib import Path

from .extract import extract_company_benchmark
from .fetch import HttpClient, discover_company_filings, select_latest_comparable
from .report import build_json_report, build_markdown_report


def _parse_candidate_slugs(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


def _resolve_urls(
    client: HttpClient,
    next_url: str | None,
    frasers_url: str | None,
    next_candidates: list[str],
    frasers_candidates: list[str],
) -> tuple[str, str]:
    if next_url and frasers_url:
        return next_url, frasers_url

    next_filings = []
    frasers_filings = []

    for slug in next_candidates:
        next_filings.extend(discover_company_filings(client, slug))
    for slug in frasers_candidates:
        frasers_filings.extend(discover_company_filings(client, slug))

    next_chosen, frasers_chosen = select_latest_comparable(next_filings, frasers_filings)

    resolved_next = next_url or (next_chosen.url if next_chosen else None)
    resolved_frasers = frasers_url or (frasers_chosen.url if frasers_chosen else None)

    if not resolved_next or not resolved_frasers:
        raise RuntimeError(
            "Could not auto-discover both report URLs. Pass --next-url and --frasers-url explicitly."
        )
    return resolved_next, resolved_frasers


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ifrs9-benchmark",
        description="Extract IFRS 9 benchmark data from report links and generate side-by-side output.",
    )
    parser.add_argument("--next-url", help="Direct report URL for Next plc (filling page or PDF).")
    parser.add_argument("--frasers-url", help="Direct report URL for Frasers Group (filling page or PDF).")
    parser.add_argument(
        "--next-slug-candidates",
        default="next-plc,next",
        help="Comma-separated slug candidates used for auto-discovery.",
    )
    parser.add_argument(
        "--frasers-slug-candidates",
        default="frasers-group-plc,frasers-group,frasers+",
        help="Comma-separated slug candidates used for auto-discovery.",
    )
    parser.add_argument(
        "--output",
        default="ifrs9_benchmark_report.md",
        help="Output markdown report path.",
    )
    parser.add_argument(
        "--json-output",
        default="ifrs9_benchmark_report.json",
        help="Output structured JSON path.",
    )
    parser.add_argument("--timeout", type=int, default=45, help="HTTP timeout in seconds.")
    parser.add_argument(
        "--max-pdf-pages",
        type=int,
        default=250,
        help="Max pages to parse for PDFs.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    client = HttpClient(timeout=args.timeout)

    next_candidates = _parse_candidate_slugs(args.next_slug_candidates)
    frasers_candidates = _parse_candidate_slugs(args.frasers_slug_candidates)
    next_url, frasers_url = _resolve_urls(
        client=client,
        next_url=args.next_url,
        frasers_url=args.frasers_url,
        next_candidates=next_candidates,
        frasers_candidates=frasers_candidates,
    )

    next_data = extract_company_benchmark(
        client=client,
        company="Next plc",
        report_url=next_url,
        max_pdf_pages=args.max_pdf_pages,
    )
    frasers_data = extract_company_benchmark(
        client=client,
        company="Frasers Group",
        report_url=frasers_url,
        max_pdf_pages=args.max_pdf_pages,
    )

    markdown = build_markdown_report(next_data, frasers_data)
    json_payload = build_json_report(next_data, frasers_data)

    output_path = Path(args.output)
    output_path.write_text(markdown, encoding="utf-8")

    json_path = Path(args.json_output)
    json_path.write_text(json_payload, encoding="utf-8")

    print(f"Resolved Next report: {next_url}")
    print(f"Resolved Frasers report: {frasers_url}")
    print(f"Markdown report written to: {output_path.resolve()}")
    print(f"JSON report written to: {json_path.resolve()}")


if __name__ == "__main__":
    main()
