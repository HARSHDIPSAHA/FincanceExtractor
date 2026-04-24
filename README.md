# IFRS 9 Benchmarking Tool

A flexible tool to compare how **multiple companies** calculate credit losses under IFRS 9.

## What You Get

Run the tool with any number of companies and get a comparison report showing:

| What | Why it matters |
|------|----------------|
| **Coverage ratio** | How much they set aside for bad debts (higher = more cautious) |
| **Model type** | Simplified (lifetime ECL) vs 3-stage IFRS 9 - affects timing of provisions |
| **Scenarios used** | How many economic scenarios they test + weightings (more = more thorough) |
| **Key assumptions** | PD (chance of default), LGD (loss if default), EAD (exposure) |
| **Ageing analysis** | % of book in each delinquency bucket (0-60, 60-120, 120+ DPD) |
| **Impairment movements** | Stage-level opening, charges, write-offs, closing balances |

## How to Run

### Quick Start (Auto-discover URLs)

```bash
cd C:\trash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Auto-discover latest reports for Next and Frasers
python -m ifrs9_benchmark --companies "Next plc,Frasers Group"
```

### With Explicit URLs (Recommended)

```bash
python -m ifrs9_benchmark \
  --companies "Next plc=https://url-to-next-report.pdf,Frasers Group=https://url-to-frasers-report.pdf" \
  --output "ifrs9_benchmark_report.md" \
  --json-output "ifrs9_benchmark_report.json"
```

### Compare 3+ Companies

```bash
python -m ifrs9_benchmark \
  --companies "Company A=https://url-a.pdf,Company B=https://url-b.pdf,Company C=https://url-c.pdf" \
  --output "report.md"
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `--companies` | **Required.** Comma-separated `Name=URL` pairs. Names only will auto-discover URLs. |
| `--candidate-slugs` | Colon-separated slug groups for auto-discovery (default: `next-plc,next:frasers-group-plc,frasers-group,frasers`) |
| `--output` | Output markdown report path (default: `ifrs9_benchmark_report.md`) |
| `--json-output` | Output JSON data path (default: `ifrs9_benchmark_report.json`) |
| `--timeout` | HTTP timeout in seconds (default: 45) |
| `--max-pdf-pages` | Max PDF pages to parse (default: 250) |

## Example Results (Next plc vs Frasers Group FY25/FY26)

### Coverage Ratio Comparison

| Metric | Next plc | Frasers Group |
|--------|----------|---------------|
| Gross exposure | £1,584.7m | £254.9m |
| ECL allowance | £(169.3)m | £(73.2)m |
| **Coverage ratio** | **10.7%** | **28.7%** |

### IFRS 9 Model Design

| Feature | Next plc | Frasers Group |
|---------|----------|---------------|
| **Model structure** | Simplified approach (lifetime ECL) | **3-stage IFRS 9 model** |
| **Scenarios** | 4 scenarios: Base(45%), Upside(5%), Downside(35%), Extreme(15%) | 4 scenarios: Base(55%), Upside(10%), Downside(30%), Extreme(5%) |
| **Coverage** | ~11% | ~29% |

### Ageing / Delinquency Analysis

| Company | Not Past Due | 0-60 days | 60-120 days | 120+ days | Total | % 120+ |
|---------|--------------|-----------|-------------|-----------|-------|--------|
| Frasers Group | £178.2m | - | - | - | £178.2m | n/a |

### Impairment Movement by Stage

| Company | Stage | Opening | Charge | Write-offs | Closing |
|---------|-------|---------|--------|------------|---------|
| Frasers Group | Stage 1 | £(17.7)m | £(6.3)m | £6.0m | £(11.7)m |
| Frasers Group | Stage 2 | £(18.9)m | £(6.3)m | £7.9m | £(17.3)m |
| Frasers Group | Stage 3 | £(44.1)m | £(18.2)m | £18.1m | £(44.2)m |

### Why the Difference?

- **Frasers uses 3-stage model** - Stage 1 (performing), Stage 2 (credit risk increase), Stage 3 (default)
- **Next uses simplified approach** - Always lifetime ECL, no staging
- Frasers has more detailed breakdown: Stage 1 coverage ~7%, Stage 2 ~39%, Stage 3 ~82%

## Output Files

- `ifrs9_benchmark_report.md` - Human-readable markdown comparison
- `ifrs9_benchmark_report.json` - Structured data for Excel/analysis

## Need Help?

- **Coverage ratio** = ECL allowance ÷ Gross receivables
- **Simplified model** = Always lifetime ECL (no staging)
- **3-stage model** = Stage 1 (performing), Stage 2 (credit risk increase), Stage 3 (default)
- **120+ DPD** = Days past due; loans >120 DPD typically in Stage 3 (credit-impaired)

## Running Tests

```bash
python -m pytest tests/test_extract.py -v
```

*Contributed by Claude AI*
