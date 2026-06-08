import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd


def main() -> int:
    batch_path = Path("tmp/batch24_securities.csv")
    batch = pd.read_csv(batch_path)
    bad: list[dict[str, str]] = []
    ok = 0
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    for _, row in batch.iterrows():
        code = row["source_code"]
        ts_code = row["ts_code"]
        snippet = (
            "from datetime import date; "
            "from core600.data_sources.baostock_source import BaoStockDataSource; "
            "s=BaoStockDataSource(); "
            f"df=s.fetch_daily_history('{code}', date(2025,6,6), date(2026,6,6)); "
            "print(len(df))"
        )
        try:
            result = subprocess.run(
                [sys.executable, "-c", snippet],
                cwd=".",
                env=env,
                capture_output=True,
                text=True,
                timeout=45,
            )
        except subprocess.TimeoutExpired:
            bad.append({"ts_code": ts_code, "source_code": code, "error": "timeout"})
            print(f"timeout {ts_code} {code}", flush=True)
            continue
        if result.returncode == 0:
            ok += 1
            if ok % 20 == 0:
                print(f"ok {ok} last {ts_code}", flush=True)
        else:
            bad.append(
                {
                    "ts_code": ts_code,
                    "source_code": code,
                    "error": result.stderr[-500:],
                }
            )
            print(f"bad {ts_code} {result.stderr[-120:]}", flush=True)
    print(f"DONE ok={ok} bad={len(bad)}")
    print(json.dumps(bad, ensure_ascii=False, indent=2))
    pd.DataFrame(bad).to_csv("tmp/batch24_bad.csv", index=False, encoding="utf-8-sig")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
