from __future__ import annotations

import re
from collections import defaultdict

from .fetch import HttpClient, extract_pdf_links
from .models import CompanyBenchmark, Evidence, ExtractedField, SourceDocument, TableData
from .parse import load_document, report_period_from_url
from .utils import (
    best_sentences,
    contains_any,
    first_number,
    normalize_space,
    parse_number,
    safe_ratio,
    split_sentences,
)


NUMBER_CAPTURE = r"(\(?-?\d[\d,]*(?:\.\d+)?\)?)"


def _field(value: str | None, snippets: list[str], source_url: str) -> ExtractedField:
    evidence = [Evidence(text=normalize_space(s), source_url=source_url) for s in snippets if normalize_space(s)]
    return ExtractedField(value=value, evidence=evidence)


def _pick_best_table(tables: list[TableData], keywords: list[str]) -> TableData | None:
    best: tuple[int, TableData] | None = None
    for table in tables:
        text = " ".join(table.columns + [cell for row in table.rows for cell in row]).lower()
        score = sum(1 for kw in keywords if kw in text)
        if score <= 0:
            continue
        if best is None or score > best[0]:
            best = (score, table)
    return best[1] if best else None


def _row_value(row: list[str]) -> float | None:
    for cell in row[1:]:
        value = first_number(cell)
        if value is not None:
            return value
    if row:
        return first_number(row[0])
    return None


def _extract_values_from_table(table: TableData) -> dict[str, float]:
    values: dict[str, float] = {}
    for row in table.rows:
        if not row:
            continue
        key = row[0].lower()
        value = _row_value(row)
        if value is None:
            continue
        values[key] = value
    return values


def _is_year_like(value: float) -> bool:
    absolute = abs(value)
    return absolute.is_integer() and 1900 <= absolute <= 2100


def _select_row_number(row: list[str], key: str) -> float | None:
    numbers = [parse_number(cell) for cell in row[1:]]
    numbers = [n for n in numbers if n is not None]
    if not numbers:
        return None

    non_year_numbers = [n for n in numbers if not _is_year_like(n)]
    if non_year_numbers:
        numbers = non_year_numbers

    low = key.lower()
    if contains_any(low, ["allowance", "impairment", "provision", "loss allowance", "expected credit loss"]):
        for number in numbers:
            if number < 0:
                return number
        chosen = max(numbers, key=lambda n: abs(n))
        if contains_any(low, ["less", "allowance", "impairment", "provision", "loss"]):
            return -abs(chosen)
        return chosen
    return numbers[0]


def _gross_row_score(key: str) -> int:
    low = key.lower()
    score = 0
    if contains_any(low, ["gross customer receivables", "gross trade receivables", "gross receivables"]):
        score += 7
    elif contains_any(low, ["gross value", "gross carrying amount"]):
        score += 5
    elif "gross" in low:
        score += 2
    if "net" in low:
        score -= 3
    return score


def _allowance_row_score(key: str) -> int:
    low = key.lower()
    score = 0
    if "allowance for expected credit loss" in low:
        score += 8
    if "allowance for expected credit losses" in low:
        score += 8
    if "provision for impairment" in low:
        score += 7
    if contains_any(low, ["allowance", "impairment", "loss allowance", "expected credit loss", "provision"]):
        score += 4
    if "less" in low:
        score += 3
    if contains_any(low, ["reversal", "charge", "movement", "opening", "closing"]):
        score -= 3
    return score


def _extract_metric_from_text(text: str, patterns: list[str]) -> float | None:
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = parse_number(match.group(1))
        if value is not None:
            return value
    return None


def _extract_core_metrics(text: str, tables: list[TableData]) -> tuple[float | None, float | None, TableData | None]:
    candidate = _pick_best_table(
        tables,
        ["receivable", "gross", "allowance", "expected credit", "impairment", "loss allowance", "net"],
    )
    gross = None
    allowance = None

    if candidate:
        gross_choice: tuple[int, float] | None = None
        allowance_choice: tuple[int, float] | None = None
        for row in candidate.rows:
            if not row:
                continue
            key = row[0]
            value = _select_row_number(row, key)
            if value is None:
                continue
            gross_score = _gross_row_score(key)
            allowance_score = _allowance_row_score(key)
            if gross_score > 0:
                candidate_score = (gross_score, abs(value))
                if gross_choice is None or candidate_score > (gross_choice[0], abs(gross_choice[1])):
                    gross_choice = (gross_score, value)
            if allowance_score > 0:
                candidate_score = (allowance_score, abs(value))
                if allowance_choice is None or candidate_score > (allowance_choice[0], abs(allowance_choice[1])):
                    allowance_choice = (allowance_score, value)
        if gross_choice:
            gross = abs(gross_choice[1])
        if allowance_choice:
            allowance = allowance_choice[1]

    if gross is None:
        gross = _extract_metric_from_text(
            text,
            [
                rf"gross\s+(?:customer\s+)?receivables[^0-9\-()]*{NUMBER_CAPTURE}",
                rf"gross\s+carrying\s+amount[^0-9\-()]*{NUMBER_CAPTURE}",
                rf"trade\s+receivables[^0-9\-()]*gross[^0-9\-()]*{NUMBER_CAPTURE}",
            ],
        )
    if allowance is None:
        allowance = _extract_metric_from_text(
            text,
            [
                rf"ecl\s+allowance[^0-9\-()]*{NUMBER_CAPTURE}",
                rf"loss\s+allowance[^0-9\-()]*{NUMBER_CAPTURE}",
                rf"impairment\s+allowance[^0-9\-()]*{NUMBER_CAPTURE}",
                rf"expected\s+credit\s+loss(?:es)?\s+allowance[^0-9\-()]*{NUMBER_CAPTURE}",
            ],
        )
    return gross, allowance, candidate


def _extract_model_structure(text: str, source_url: str) -> ExtractedField:
    low = text.lower()
    pieces: list[str] = []
    has_three_stage = "stage 1" in low and "stage 2" in low and "stage 3" in low
    if has_three_stage:
        pieces.append("3-stage IFRS 9 model")
    elif "simplified approach" in low or "always lifetime" in low:
        pieces.append("Simplified approach (lifetime ECL)")
    if not pieces and "lifetime expected credit losses" in low:
        pieces.append("Lifetime ECL approach")

    seg_sentences = best_sentences(
        text,
        ["segmentation", "arrears", "bucket", "indebtedness", "behavioural", "behavioral", "credit risk"],
        limit=3,
    )
    if seg_sentences:
        pieces.append("Segmentation logic disclosed")

    value = "; ".join(pieces) if pieces else None
    return _field(value, seg_sentences[:2], source_url)


def _extract_scenario_design(text: str, source_url: str) -> ExtractedField:
    keywords = [
        "scenario",
        "weight",
        "base case",
        "upside",
        "downside",
        "severe downside",
        "macroeconomic",
    ]
    raw_evidence = best_sentences(text, keywords, limit=6)
    evidence = list(dict.fromkeys(raw_evidence))[:4]
    scenario_names: set[str] = set()
    for sentence in evidence:
        for name in [
            "base",
            "upside",
            "downside",
            "severe downside",
            "severe-case",
            "severe case",
            "extreme",
            "optimistic",
            "pessimistic",
            "central",
        ]:
            if name in sentence.lower():
                normalized = name.title()
                if name in {"severe downside", "severe-case", "severe case", "extreme"}:
                    normalized = "Extreme"
                scenario_names.add(normalized)

    joined_evidence = " ".join(evidence).lower()
    scenario_weight_patterns = {
        "Base": [r"base(?:\s+case)?[^%]{0,80}(\d{1,3}(?:\.\d+)?)\s*%"],
        "Upside": [r"upside[^%]{0,80}(\d{1,3}(?:\.\d+)?)\s*%"],
        "Downside": [r"downside[^%]{0,80}(\d{1,3}(?:\.\d+)?)\s*%"],
        "Extreme": [
            r"extreme[^%]{0,80}(\d{1,3}(?:\.\d+)?)\s*%",
            r"severe(?:[-\s]case|[-\s]downside)?[^%]{0,80}(\d{1,3}(?:\.\d+)?)\s*%",
        ],
    }
    ordered_weights: list[str] = []
    for scenario_name in ["Base", "Upside", "Downside", "Extreme"]:
        patterns = scenario_weight_patterns.get(scenario_name, [])
        for pattern in patterns:
            match = re.search(pattern, joined_evidence)
            if match:
                ordered_weights.append(match.group(1))
                break
    if ordered_weights:
        weights = ordered_weights
    else:
        weights = re.findall(r"(?<!\d)(\d{1,3}(?:\.\d+)?)\s*%", " ".join(evidence))
    value_parts = []
    if scenario_names:
        preferred_order = ["Base", "Upside", "Downside", "Extreme", "Central", "Optimistic", "Pessimistic"]
        ordered = [name for name in preferred_order if name in scenario_names]
        extras = sorted(scenario_names - set(ordered))
        ordered.extend(extras)
        value_parts.append(f"{len(ordered)} scenarios: {', '.join(ordered)}")
    if weights:
        value_parts.append(f"weights: {'/'.join(weights)}")
    value = "; ".join(value_parts) if value_parts else None
    return _field(value, evidence, source_url)


def _extract_key_parameters(text: str, source_url: str) -> ExtractedField:
    pd = best_sentences(text, ["pd", "probability of default"], limit=2)
    lgd = best_sentences(text, ["lgd", "loss given default"], limit=2)
    ead = best_sentences(text, ["ead", "exposure at default"], limit=2)
    fwd = best_sentences(
        text,
        ["unemployment", "gdp", "inflation", "interest rate", "house price", "forward-looking", "macro"],
        limit=3,
    )

    summary = []
    if pd:
        summary.append("PD disclosed")
    if lgd:
        summary.append("LGD disclosed")
    if ead:
        summary.append("EAD disclosed")
    if fwd:
        summary.append("Forward-looking variables disclosed")
    value = "; ".join(summary) if summary else None
    return _field(value, (pd + lgd + ead + fwd)[:6], source_url)


def _extract_staging_table(tables: list[TableData]) -> TableData | None:
    best: tuple[int, TableData] | None = None
    for table in tables:
        score = 0
        text = " ".join(table.columns + [cell for row in table.rows for cell in row]).lower()
        if "stage 1" in text and "stage 2" in text and "stage 3" in text:
            score += 6
        labels = [row[0].lower() for row in table.rows if row]
        if any("gross" in label and "receivable" in label for label in labels):
            score += 4
        if any(contains_any(label, ["allowance", "impairment", "expected credit loss"]) for label in labels):
            score += 4
        if any("opening" in label for label in labels) and any("closing" in label for label in labels):
            score += 2
        if score <= 0:
            continue
        if best is None or score > best[0]:
            best = (score, table)
    return best[1] if best else None


def _extract_ageing_table(tables: list[TableData]) -> TableData | None:
    return _pick_best_table(tables, ["past due", "not past due", "0-60", "60-120", "120+"])


def _extract_impairment_movement_table(tables: list[TableData]) -> TableData | None:
    return _pick_best_table(tables, ["opening", "charge", "write-off", "closing", "stage"])


def _append_stage_coverage_note(company: CompanyBenchmark) -> None:
    table = company.staging_table
    if not table:
        return
    lower_columns = [col.lower() for col in table.columns]
    stage_indices = {}
    for idx, col in enumerate(lower_columns):
        if "stage 1" in col:
            stage_indices["Stage 1"] = idx
        elif "stage 2" in col:
            stage_indices["Stage 2"] = idx
        elif "stage 3" in col:
            stage_indices["Stage 3"] = idx
    if not stage_indices:
        return

    gross_row = None
    allowance_row = None
    for row in table.rows:
        if not row:
            continue
        label = row[0].lower()
        if "gross" in label:
            gross_row = row
        if "allowance" in label or "impairment" in label or "expected credit loss" in label:
            allowance_row = row
    if not gross_row or not allowance_row:
        return

    parts = []
    for stage_name, idx in sorted(stage_indices.items()):
        if idx >= len(gross_row) or idx >= len(allowance_row):
            continue
        gross = first_number(gross_row[idx])
        allowance = first_number(allowance_row[idx])
        if gross is None or allowance is None or gross == 0:
            continue
        ratio = abs(allowance) / abs(gross)
        parts.append(f"{stage_name}: {ratio * 100:.1f}%")
    if parts:
        company.notes.append("Stage-level coverage ratios -> " + ", ".join(parts))


def _collect_documents(client: HttpClient, report_url: str, max_pdf_pages: int) -> list[SourceDocument]:
    primary = load_document(client, report_url, max_pdf_pages=max_pdf_pages)
    docs = [primary]
    if primary.document_type == "html":
        pdf_links: list[str] = []
        # Also parse HTML source for real links.
        try:
            html_raw = client.get_text(report_url)
            pdf_links = extract_pdf_links(html_raw, report_url) or pdf_links
        except Exception:
            pass
        for pdf_link in pdf_links[:2]:
            try:
                docs.append(load_document(client, pdf_link, max_pdf_pages=max_pdf_pages))
            except Exception:
                continue
    return docs


def extract_company_benchmark(
    client: HttpClient,
    company: str,
    report_url: str,
    max_pdf_pages: int = 250,
) -> CompanyBenchmark:
    docs = _collect_documents(client, report_url, max_pdf_pages=max_pdf_pages)
    merged_text = "\n".join(doc.text for doc in docs if doc.text)
    all_tables: list[TableData] = []
    for doc in docs:
        all_tables.extend(doc.tables)

    source_anchor = docs[0].url if docs else report_url
    model = _extract_model_structure(merged_text, source_anchor)
    scenario = _extract_scenario_design(merged_text, source_anchor)
    key_params = _extract_key_parameters(merged_text, source_anchor)

    gross, allowance, core_table = _extract_core_metrics(merged_text, all_tables)
    explicit_ratio = _extract_metric_from_text(
        merged_text,
        [r"coverage\s+ratio[^0-9]*(\d{1,3}(?:\.\d+)?)\s*%", r"allowance\s+rate[^0-9]*(\d{1,3}(?:\.\d+)?)\s*%"],
    )
    ratio = (
        explicit_ratio / 100
        if explicit_ratio is not None
        else safe_ratio(
            abs(allowance) if allowance is not None else None,
            abs(gross) if gross is not None else None,
        )
    )
    method = "disclosed" if explicit_ratio is not None else ("derived" if ratio is not None else None)

    benchmark = CompanyBenchmark(
        company=company,
        report_url=report_url,
        report_period=report_period_from_url(report_url),
        model_structure=model,
        scenario_design=scenario,
        key_parameters=key_params,
        gross_exposure=abs(gross) if gross is not None else None,
        ecl_allowance=allowance,
        coverage_ratio=ratio,
        coverage_ratio_method=method,
        core_ecl_table=core_table,
        staging_table=_extract_staging_table(all_tables),
        ageing_table=_extract_ageing_table(all_tables),
        impairment_movement_table=_extract_impairment_movement_table(all_tables),
        source_documents=[doc.url for doc in docs],
    )

    if benchmark.coverage_ratio is None:
        benchmark.notes.append("Coverage ratio unavailable from extracted data.")
    if benchmark.model_structure.value is None:
        benchmark.notes.append("Model structure not confidently extracted; validate manually.")
    _append_stage_coverage_note(benchmark)
    return benchmark


def evidence_to_text(field: ExtractedField) -> str:
    snippets = [e.text for e in field.evidence if e.text]
    return " | ".join(snippets)


def keyword_density(text: str, keywords: list[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    lines = split_sentences(text)
    for line in lines:
        low = line.lower()
        for keyword in keywords:
            if keyword.lower() in low:
                counts[keyword] += 1
    return counts
