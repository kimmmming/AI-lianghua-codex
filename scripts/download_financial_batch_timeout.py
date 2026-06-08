import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from core600.financial_data import recent_quarters
from core600.market_data import select_market_data_securities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-basic-path", type=Path, required=True)
    parser.add_argument("--batch-number", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--lookback-quarters", type=int, default=6)
    parser.add_argument("--timeout-seconds", type=int, default=90)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    as_of_date = date.fromisoformat(args.as_of_date)
    stock_basic = pd.read_parquet(args.stock_basic_path)
    securities = select_market_data_securities(stock_basic, as_of_date)
    batch_start = (args.batch_number - 1) * args.batch_size
    batch = securities.iloc[batch_start : batch_start + args.batch_size]
    batch_dir = args.output_dir / f"financial_latest_{as_of_date.isoformat()}_batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_path = batch_dir / f"batch_{args.batch_number:05d}.parquet"
    errors_path = batch_dir / f"batch_{args.batch_number:05d}_errors.json"
    tmp_dir = Path("tmp/financial_batch_timeout") / f"batch_{args.batch_number:05d}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    quarters = recent_quarters(as_of_date, args.lookback_quarters)

    frames: list[pd.DataFrame] = []
    errors: list[dict[str, str]] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    quarter_literal = repr(quarters)
    for row in batch.itertuples(index=False):
        out_path = tmp_dir / f"{row.ts_code}.parquet"
        snippet = (
            "from datetime import date; "
            "from pathlib import Path; "
            "import pandas as pd; "
            "from core600.data_sources.baostock_source import BaoStockDataSource; "
            "from core600.financial_data import fetch_latest_financial_for_security; "
            "s=BaoStockDataSource(); "
            f"prepared=fetch_latest_financial_for_security(s, '{row.ts_code}', '{row.source_code}', "
            f"date({as_of_date.year},{as_of_date.month},{as_of_date.day}), {quarter_literal}, "
            "pd.Timestamp.utcnow().to_pydatetime()); "
            f"prepared.to_parquet(Path(r'{out_path}'), index=False); "
            "print(len(prepared))"
        )
        try:
            result = subprocess.run(
                [sys.executable, "-c", snippet],
                cwd=".",
                env=env,
                capture_output=True,
                text=True,
                timeout=args.timeout_seconds,
            )
        except subprocess.TimeoutExpired:
            errors.append({"ts_code": row.ts_code, "source_code": row.source_code, "error": "timeout"})
            print(f"timeout {row.ts_code}", flush=True)
            continue
        if result.returncode != 0:
            errors.append(
                {
                    "ts_code": row.ts_code,
                    "source_code": row.source_code,
                    "error": result.stderr[-500:],
                }
            )
            print(f"error {row.ts_code}", flush=True)
            continue
        if out_path.exists():
            frame = pd.read_parquet(out_path)
            if not frame.empty:
                frames.append(frame)
        if len(frames) % 20 == 0:
            print(f"ok={len(frames)} latest={row.ts_code}", flush=True)

    batch_data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    batch_data.to_parquet(batch_path, index=False)
    errors_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"financial_batch={args.batch_number} securities={len(batch)} rows={len(batch_data)} "
        f"errors={len(errors)} path={batch_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
