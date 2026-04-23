# IFRS 9 Benchmarking Tool

A simple tool to compare how **Next plc** and **Frasers Group** calculate credit losses under IFRS 9.

## What You Get

Just run the tool and you'll get a comparison report showing:

| What | Why it matters |
|------|----------------|
| **Coverage ratio** | How much they set aside for bad debts (higher = more cautious) |
| **Model type** | Simplified (Next) vs 3-stage (Frasers) - affects timing of provisions |
| **Scenarios used** | How many economic scenarios they test (more = more thorough) |
| **Key assumptions** | PD (chance of default), LGD (loss if default), EAD (exposure) |

## How to Run (3 Steps)

### Step 1: Install Python (if not installed)
- Download from [python.org](https://www.python.org/downloads/)
- Check "Add to PATH" during installation

### Step 2: Open Command Prompt
Press `Win + R`, type `cmd`, press Enter

### Step 3: Run These Commands

```cmd
cd C:\trash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m ifrs9_benchmark --next-url "https://www.nextplc.co.uk/~/media/Files/N/next-plc-v4/about-next/annual-report-and-accounts-jan-2026.pdf" --frasers-url "https://frasers-cms.netlify.app/assets/files/financials/fg-annual-report-2025-web.pdf" --output "ifrs9_benchmark_report.md" --json-output "ifrs9_benchmark_report.json"
```

That's it! You'll get two files:
- `ifrs9_benchmark_report.md` - readable comparison
- `ifrs9_benchmark_report.json` - data for Excel

## Quick Test

Want to try without links? Just run:
```cmd
python -m ifrs9_benchmark
```

It will automatically find the latest reports (may take a few seconds).

## Example Results (Next plc vs Frasers Group FY25/FY26)

### Coverage Ratio Comparison

| Metric | Next plc | Frasers Group |
|--------|----------|---------------|
| Gross exposure | £1,584.7m | £254.9m |
| ECL allowance | £(169.3)m | £(73.2)m |
| **Coverage ratio** | **10.7%** | **28.7%** |

### Key Differences

| Feature | Next plc | Frasers Group |
|---------|----------|---------------|
| **Model structure** | Simplified approach (lifetime ECL) | **3-stage IFRS 9 model** |
| **Scenarios** | 4 scenarios: Base(45%), Upside(5%), Downside(35%), Extreme(15%) | 4 scenarios: Base(55%), Upside(10%), Downside(30%), Extreme(5%) |
| **Coverage** | ~11% | ~29% |

### Why the Difference?

- **Frasers uses 3-stage model** - Stage 1 (performing), Stage 2 (credit risk increase), Stage 3 (default)
- **Next uses simplified approach** - Always lifetime ECL, no staging
- Frasers has more detailed breakdown: Stage 1 coverage ~7%, Stage 2 ~39%, Stage 3 ~82%

### Frasers Group - Stage Breakdown (2025)

| Stage | Gross Receivables | ECL Allowance | Coverage |
|-------|-------------------|---------------|----------|
| Stage 1 | £157.6m | £(11.7m) | 7.4% |
| Stage 2 | £43.4m | £(17.3m) | 39.9% |
| Stage 3 | £53.9m | £(44.2m) | 82.0% |

## Need Help?

- **Coverage ratio** = ECL allowance ÷ Gross receivables
- **Simplified model** = Always lifetime ECL (no staging)
- **3-stage model** = Stage 1 (performing), Stage 2 (credit risk increase), Stage 3 (default)

*Contributed by Claude AI*
