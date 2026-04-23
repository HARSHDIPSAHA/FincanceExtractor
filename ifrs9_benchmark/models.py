from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass(slots=True)
class Evidence:
    text: str
    source_url: str
    location: str | None = None


@dataclass(slots=True)
class ExtractedField:
    value: str | None = None
    evidence: list[Evidence] = field(default_factory=list)


@dataclass(slots=True)
class TableData:
    title: str
    columns: list[str]
    rows: list[list[str]]
    source_url: str
    location: str | None = None


@dataclass(slots=True)
class FilingLink:
    slug: str
    kind: str
    year: int
    filing_id: str | None
    url: str


@dataclass(slots=True)
class SourceDocument:
    url: str
    document_type: str
    text: str
    tables: list[TableData] = field(default_factory=list)


@dataclass(slots=True)
class CompanyBenchmark:
    company: str
    report_url: str
    report_period: str | None
    model_structure: ExtractedField
    scenario_design: ExtractedField
    key_parameters: ExtractedField
    gross_exposure: float | None = None
    ecl_allowance: float | None = None
    coverage_ratio: float | None = None
    coverage_ratio_method: str | None = None
    core_ecl_table: TableData | None = None
    staging_table: TableData | None = None
    ageing_table: TableData | None = None
    impairment_movement_table: TableData | None = None
    notes: list[str] = field(default_factory=list)
    source_documents: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
