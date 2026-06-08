import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from core600.market_data import select_market_data_securities


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stock-basic-path", type=Path, required=True)
    parser.add_argument("--batch-number", type=int, required=True)
    parser.add_argument("--batch-size", type=int, default=200)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw"))
    parser.add_argument("--timeout-seconds", type=int, default=60)
    parser.add_argument("--skip-source-codes-file", type=Path, default=None)
    return parser.parse_args()


def read_skip(path: Path | None) -> set[str]:
    if path is None:
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def main() -> int:
    args = parse_args()
    as_of_date = date.fromisoformat(args.as_of_date)
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    stock_basic = pd.read_parquet(args.stock_basic_path)
    securities = select_market_data_securities(stock_basic, as_of_date)
    batch_start = (args.batch_number - 1) * args.batch_size
    batch = securities.iloc[batch_start : batch_start + args.batch_size]
    batch_dir = args.output_dir / f"market_daily_{as_of_date.isoformat()}_batches"
    batch_dir.mkdir(parents=True, exist_ok=True)
    batch_path = batch_dir / f"batch_{args.batch_number:05d}.parquet"
    errors_path = batch_dir / f"batch_{args.batch_number:05d}_errors.json"
    tmp_dir = Path("tmp/market_batch_timeout") / f"batch_{args.batch_number:05d}"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    skip = read_skip(args.skip_source_codes_file)

    frames: list[pd.DataFrame] = []
    errors: list[dict[str, str]] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    for row in batch.itertuples(index=False):
        if row.source_code in skip:
            errors.append(
                {"ts_code": row.ts_code, "source_code": row.source_code, "error": "configured_skip"}
            )
            continue
        out_path = tmp_dir / f"{row.ts_code}.parquet"
        snippet = (
            "from datetime import date; "
            "from pathlib import Path; "
            "import pandas as pd; "
            "from core600.data_sources.baostock_source import BaoStockDataSource; "
            "from core600.market_data import prepare_daily_history; "
            "s=BaoStockDataSource(); "
            f"raw=s.fetch_daily_history('{row.source_code}', date({start_date.year},{start_date.month},{start_date.day}), date({end_date.year},{end_date.month},{end_date.day})); "
            f"prepared=prepare_daily_history(raw, '{row.ts_code}', '{row.source_code}', date({as_of_date.year},{as_of_date.month},{as_of_date.day}), pd.Timestamp.utcnow().to_pydatetime()); "
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
            frames.append(pd.read_parquet(out_path))
        if len(frames) % 20 == 0:
            print(f"ok={len(frames)} latest={row.ts_code}", flush=True)

    batch_data = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    batch_data.to_parquet(batch_path, index=False)
    errors_path.write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"batch={args.batch_number} securities={len(batch)} rows={len(batch_data)} "
        f"errors={len(errors)} path={batch_path}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
