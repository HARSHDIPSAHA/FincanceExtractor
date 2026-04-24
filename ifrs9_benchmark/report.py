from __future__ import annotations

import json
from dataclasses import asdict

from .models import AgeingBucket, CompanyBenchmark, StageMovement, TableData
from .utils import fmt_number, fmt_percent


def _md_escape(value: str) -> str:
    return value.replace("|", "\\|")


def table_to_markdown(table: TableData | None) -> str:
    if table is None:
        return "_No disclosed table extracted._"
    header = table.columns or []
    if not header and table.rows:
        header = [f"col_{idx+1}" for idx in range(len(table.rows[0]))]
    if not header:
        return "_No disclosed table extracted._"
    lines = []
    lines.append("| " + " | ".join(_md_escape(col or "") for col in header) + " |")
    lines.append("| " + " | ".join("---" for _ in header) + " |")
    for row in table.rows:
        padded = list(row) + [""] * max(0, len(header) - len(row))
        lines.append("| " + " | ".join(_md_escape(str(cell)) for cell in padded[: len(header)]) + " |")
    lines.append(f"\nSource: {table.source_url}")
    return "\n".join(lines)


def _joined_values(values: list[str]) -> str:
    filtered = [v for v in values if v]
    return "; ".join(filtered) if filtered else "n/a"


def build_markdown_report(companies: list[CompanyBenchmark]) -> str:
    """Build markdown report for N companies."""
    if len(companies) < 2:
        raise ValueError("Need at least 2 companies for comparison")

    lines: list[str] = []

    company_names = " vs ".join(c.company for c in companies[:3])
    if len(companies) > 3:
        company_names += f" (+{len(companies) - 3} more)"

    lines.append(f"# IFRS 9 Benchmarking Report ({company_names})")
    lines.append("")
    lines.append("## Source reports")
    lines.append("")
    for company in companies:
        lines.append(f"- **{company.company}:** {company.report_url} ({company.report_period or 'period not detected'})")
    lines.append("")

    lines.append("## 1) Core ECL / Coverage side-by-side")
    lines.append("")
    header = "| Metric |" + " | ".join(c.company for c in companies) + " |"
    separator = "| --- |" + " | ".join("---" for _ in companies) + " |"
    lines.append(header)
    lines.append(separator)

    metrics = [
        ("Gross exposure", lambda c: fmt_number(c.gross_exposure)),
        ("ECL allowance", lambda c: fmt_number(c.ecl_allowance)),
        ("Coverage ratio", lambda c: fmt_percent(c.coverage_ratio)),
        ("Coverage method", lambda c: c.coverage_ratio_method or "n/a"),
    ]
    for label, accessor in metrics:
        row = f"| {label} |" + " | ".join(accessor(c) for c in companies) + " |"
        lines.append(row)
    lines.append("")

    lines.append("## 2) IFRS 9 model design benchmark")
    lines.append("")
    lines.append("| Feature |" + " | ".join(c.company for c in companies) + " |")
    lines.append("| --- |" + " | ".join("---" for _ in companies) + " |")

    features = [
        ("Model structure", lambda c: c.model_structure.value or "n/a"),
        ("Scenario design", lambda c: c.scenario_design.value or "n/a"),
        ("PD/LGD/EAD + forward-looking", lambda c: c.key_parameters.value or "n/a"),
    ]
    for label, accessor in features:
        row = f"| {label} |" + " | ".join(_md_escape(accessor(c)) for c in companies) + " |"
        lines.append(row)
    lines.append("")

    lines.append("## 3) Ageing / Delinquency Analysis")
    lines.append("")
    lines.append("| Company | Not Past Due | 0-60 days | 60-120 days | 120+ days | Total | % 120+ |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for company in companies:
        buckets = {b.bucket_name: b for b in company.ageing_buckets}
        not_past_due = buckets.get("Not Past Due", None)
        d0_60 = buckets.get("0-60 Days", None)
        d60_120 = buckets.get("60-120 Days", None)
        d120_plus = buckets.get("120+ Days", None)

        def fmt_bucket(b: AgeingBucket | None) -> str:
            if b and b.gross_amount:
                return fmt_number(b.gross_amount)
            return "-"

        total = sum(b.gross_amount or 0 for b in company.ageing_buckets)
        pct_120 = (d120_plus.gross_amount / total * 100) if d120_plus and d120_plus.gross_amount and total else None

        row = f"| {company.company} | {fmt_bucket(not_past_due)} | {fmt_bucket(d0_60)} | {fmt_bucket(d60_120)} | {fmt_bucket(d120_plus)} | {fmt_number(total)} | {fmt_percent(pct_120)} |"
        lines.append(row)
    lines.append("")

    lines.append("## 4) Impairment Movement Analysis")
    lines.append("")
    lines.append("| Company | Stage | Opening | Charge | Write-offs | Closing |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for company in companies:
        if not company.stage_movements:
            continue
        for mov in sorted(company.stage_movements, key=lambda m: m.stage):
            row = f"| {company.company} | {mov.stage} | {fmt_number(mov.opening)} | {fmt_number(mov.charge)} | {fmt_number(mov.write_offs)} | {fmt_number(mov.closing)} |"
            lines.append(row)
    lines.append("")

    lines.append("## 5) Evidence excerpts")
    lines.append("")
    lines.append("| Item |" + " | ".join(c.company for c in companies) + " |")
    lines.append("| --- |" + " | ".join("---" for _ in companies) + " |")

    evidence_items = [
        ("Model structure", lambda c: _joined_values([e.text for e in c.model_structure.evidence])),
        ("Scenario design", lambda c: _joined_values([e.text for e in c.scenario_design.evidence])),
        ("Key parameters", lambda c: _joined_values([e.text for e in c.key_parameters.evidence])),
    ]
    for label, accessor in evidence_items:
        row = f"| {label} |" + " | ".join(_md_escape(accessor(c)[:500] + "..." if len(accessor(c)) > 500 else accessor(c)) for c in companies) + " |"
        lines.append(row)
    lines.append("")

    lines.append("## 6) Extracted disclosed table excerpts")
    lines.append("")
    for company in companies:
        lines.append(f"### {company.company} - Core ECL table")
        lines.append("")
        lines.append(table_to_markdown(company.core_ecl_table))
        lines.append("")

        if company.staging_table:
            lines.append(f"### {company.company} - Stage table")
            lines.append("")
            lines.append(table_to_markdown(company.staging_table))
            lines.append("")

        if company.ageing_table:
            lines.append(f"### {company.company} - Ageing table")
            lines.append("")
            lines.append(table_to_markdown(company.ageing_table))
            lines.append("")

        if company.impairment_movement_table:
            lines.append(f"### {company.company} - Impairment movement table")
            lines.append("")
            lines.append(table_to_markdown(company.impairment_movement_table))
            lines.append("")

    lines.append("## 7) Analyst notes")
    lines.append("")
    has_notes = False
    for company in companies:
        if company.notes:
            has_notes = True
            for note in company.notes:
                lines.append(f"- **{company.company}:** {note}")
    if not has_notes:
        lines.append("- No additional extraction notes.")
    lines.append("")

    return "\n".join(lines)


def build_json_report(companies: list[CompanyBenchmark]) -> str:
    """Build JSON report for N companies."""
    payload = {c.company.replace(" ", "_").lower(): asdict(c) for c in companies}
    return json.dumps(payload, indent=2, ensure_ascii=True)
