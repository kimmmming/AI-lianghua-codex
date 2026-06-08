# AGENTS.md

## Project purpose

This repository builds a reproducible and auditable A-share Core 600
candidate universe for quantitative research.

It does not provide investment advice and must not fabricate financial data.

## Non-negotiable rules

1. Never use data published after the requested as_of_date.
2. Financial data must preserve both report_period and announcement_date.
3. A financial record becomes usable only after announcement_date.
4. Historical universe construction must include delisted securities where data exists.
5. Never use the current Core 600 list to backtest historical periods.
6. Never optimize parameters solely to improve historical returns.
7. Never silently fill critical missing financial data with zero.
8. Never treat negative PE as cheap valuation.
9. Never change factor weights without an explicit user instruction.
10. Never output a stock as selected without preserving its raw factor values,
    normalized scores, exclusion checks, and selection reason.

## Engineering rules

- Python 3.11+
- Type hints required for public functions.
- Tests required for calculation logic.
- Configuration belongs in YAML, not hard-coded thresholds.
- Raw input data must never be modified in place.
- Generated files must include an as_of_date.
- Run tests before claiming completion.

## Required validation

Every selection run must verify:

- unique security identifiers;
- valid trading dates;
- no duplicated financial records;
- announcement_date is not after as_of_date;
- factor coverage and missing rates;
- exactly 600 selections unless fewer than 600 securities qualify;
- industry minimum and maximum constraints;
- deterministic output for identical inputs and configuration.

## Current stage restrictions

- Do not download stock data in stage 1.
- Do not generate a Core 600 list in stage 1.
- Do not implement full factor formulas until the required data fields are available and tested.
- Mark uncertain business rules as TODO instead of guessing.
