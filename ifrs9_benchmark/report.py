from __future__ import annotations

import json
from dataclasses import asdict

from .models import CompanyBenchmark, TableData
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


def _pair_row(label: str, left: str, right: str) -> str:
    return f"| {label} | {left} | {right} |"


def _joined_values(values: list[str]) -> str:
    filtered = [v for v in values if v]
    return "; ".join(filtered) if filtered else "n/a"


def build_markdown_report(next_data: CompanyBenchmark, frasers_data: CompanyBenchmark) -> str:
    lines: list[str] = []
    lines.append("# IFRS 9 Benchmarking Report (Next plc vs Frasers Group)")
    lines.append("")
    lines.append("## Source reports")
    lines.append("")
    lines.append(f"- **Next plc:** {next_data.report_url} ({next_data.report_period or 'period not detected'})")
    lines.append(f"- **Frasers Group:** {frasers_data.report_url} ({frasers_data.report_period or 'period not detected'})")
    lines.append("")
    lines.append("## 1) Core ECL / Coverage side-by-side")
    lines.append("")
    lines.append("| Metric | Next plc | Frasers Group |")
    lines.append("| --- | --- | --- |")
    lines.append(_pair_row("Gross exposure", fmt_number(next_data.gross_exposure), fmt_number(frasers_data.gross_exposure)))
    lines.append(_pair_row("ECL allowance", fmt_number(next_data.ecl_allowance), fmt_number(frasers_data.ecl_allowance)))
    lines.append(_pair_row("Coverage ratio", fmt_percent(next_data.coverage_ratio), fmt_percent(frasers_data.coverage_ratio)))
    lines.append(
        _pair_row(
            "Coverage method",
            next_data.coverage_ratio_method or "n/a",
            frasers_data.coverage_ratio_method or "n/a",
        )
    )
    lines.append("")
    lines.append("## 2) IFRS 9 model design benchmark")
    lines.append("")
    lines.append("| Feature | Next plc | Frasers Group |")
    lines.append("| --- | --- | --- |")
    lines.append(
        _pair_row(
            "Model structure",
            next_data.model_structure.value or "n/a",
            frasers_data.model_structure.value or "n/a",
        )
    )
    lines.append(
        _pair_row(
            "Scenario design",
            next_data.scenario_design.value or "n/a",
            frasers_data.scenario_design.value or "n/a",
        )
    )
    lines.append(
        _pair_row(
            "PD/LGD/EAD + forward-looking variables",
            next_data.key_parameters.value or "n/a",
            frasers_data.key_parameters.value or "n/a",
        )
    )
    lines.append("")
    lines.append("## 3) Evidence excerpts")
    lines.append("")
    lines.append("| Item | Next plc evidence | Frasers Group evidence |")
    lines.append("| --- | --- | --- |")
    lines.append(
        _pair_row(
            "Model structure",
            _joined_values([ev.text for ev in next_data.model_structure.evidence]),
            _joined_values([ev.text for ev in frasers_data.model_structure.evidence]),
        )
    )
    lines.append(
        _pair_row(
            "Scenario design",
            _joined_values([ev.text for ev in next_data.scenario_design.evidence]),
            _joined_values([ev.text for ev in frasers_data.scenario_design.evidence]),
        )
    )
    lines.append(
        _pair_row(
            "Key parameters",
            _joined_values([ev.text for ev in next_data.key_parameters.evidence]),
            _joined_values([ev.text for ev in frasers_data.key_parameters.evidence]),
        )
    )
    lines.append("")
    lines.append("## 4) Extracted disclosed table excerpts")
    lines.append("")
    lines.append("### Next plc - Core ECL table")
    lines.append("")
    lines.append(table_to_markdown(next_data.core_ecl_table))
    lines.append("")
    lines.append("### Frasers Group - Core ECL table")
    lines.append("")
    lines.append(table_to_markdown(frasers_data.core_ecl_table))
    lines.append("")
    lines.append("### Frasers Group - Stage table")
    lines.append("")
    lines.append(table_to_markdown(frasers_data.staging_table))
    lines.append("")
    lines.append("### Frasers Group - Ageing table")
    lines.append("")
    lines.append(table_to_markdown(frasers_data.ageing_table))
    lines.append("")
    lines.append("### Frasers Group - Impairment movement table")
    lines.append("")
    lines.append(table_to_markdown(frasers_data.impairment_movement_table))
    lines.append("")
    lines.append("## 5) Analyst notes")
    lines.append("")
    if next_data.notes:
        lines.extend([f"- Next plc: {note}" for note in next_data.notes])
    if frasers_data.notes:
        lines.extend([f"- Frasers Group: {note}" for note in frasers_data.notes])
    if not next_data.notes and not frasers_data.notes:
        lines.append("- No additional extraction notes.")
    lines.append("")
    return "\n".join(lines)


def build_json_report(next_data: CompanyBenchmark, frasers_data: CompanyBenchmark) -> str:
    payload = {
        "next_plc": asdict(next_data),
        "frasers_group": asdict(frasers_data),
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)
