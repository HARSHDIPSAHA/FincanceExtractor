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
python -m ifrs9_benchmark --next-url "https://financialreports.eu/filings/next-plc/annual-report/2025/5828452/" --frasers-url "https://financialreports.eu/filings/frasers-group-plc/annual-report/2025/7773263/"
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

## Need Help?

- **Coverage ratio** = ECL allowance ÷ Gross receivables
- **Simplified model** = Always lifetime ECL (no staging)
- **3-stage model** = Stage 1 (performing), Stage 2 (credit risk increase), Stage 3 (default)
