#!/usr/bin/env python3
"""
10,000-Row Offline Data Cleaning Benchmark
Generates a 10,000-row dirty B2B invoice CSV (duplicates, mixed dates, country aliases,
currency formatting, and spend dashes) and runs deterministic Inspect -> Fix -> Verify checks.
"""

import csv
import random
import time
from pathlib import Path
import numpy as np
import pandas as pd


COUNTRY_MAP = {
    "usa": "United States",
    "u.s.a.": "United States",
    "us": "United States",
    "united states": "United States",
    "uk": "United Kingdom",
    "u.k.": "United Kingdom",
    "united kingdom": "United Kingdom",
    "deutschland": "Germany",
    "germany": "Germany",
    "de": "Germany",
    "france": "France",
    "fr": "France",
    "canada": "Canada",
    "ca": "Canada",
}


def generate_messy_csv(path: Path, n_rows: int = 10_000) -> None:
    random.seed(42)
    countries = list(COUNTRY_MAP.keys())
    dates = ["2026-03-14", "03/14/2026", "14-03-2026", "2026.03.14", "14 Mar 2026"]
    statuses = ["active", "Active", "enabled", "TRUE", "1", "inactive", "0"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "country", "total_spend", "signup_date", "status"])
        for i in range(n_rows):
            cid = f"CUST-{i // 100 * 100 + (i % 97):05d}" if i % 15 == 0 else f"CUST-{i:05d}"
            spend = "-" if i % 9 == 0 else ("N/A" if i % 23 == 0 else f"{random.uniform(49, 4900):,.2f}")
            w.writerow([cid, random.choice(countries), spend, random.choice(dates), random.choice(statuses)])


def inspect_fix_verify(input_csv: Path, output_csv: Path) -> dict:
    t0 = time.perf_counter()
    df = pd.read_csv(input_csv, dtype=str, keep_default_na=False)
    raw_rows = len(df)

    # 1. Deduplicate deterministically
    df = df.drop_duplicates(subset=["customer_id"], keep="first").copy()

    # 2. Preserve true missing spend as NaN (never fill dashes with 0)
    spend_raw = df["total_spend"].str.replace(",", "", regex=False).replace({"-": np.nan, "N/A": np.nan, "": np.nan})
    df["total_spend"] = pd.to_numeric(spend_raw, errors="coerce")

    # 3. Parse mixed date formats into ISO-8601
    df["signup_date"] = pd.to_datetime(df["signup_date"], format="mixed", errors="coerce").dt.strftime("%Y-%m-%d")

    # 4. Canonicalize countries + statuses
    df["country"] = df["country"].str.strip().str.lower().map(COUNTRY_MAP).fillna(df["country"])
    df["status"] = np.where(df["status"].str.lower().isin(["active", "enabled", "true", "1"]), "Active", "Inactive")

    # 5. Schema assertions
    assert df["customer_id"].is_unique, "Duplicate IDs survived!"
    assert df["total_spend"].isna().sum() > 0, "Expected preserved NaNs!"
    assert pd.api.types.is_numeric_dtype(df["total_spend"]), "Spend must be numeric!"
    assert not df["signup_date"].isna().any(), "Unparsed dates remain!"
    assert set(df["status"].unique()).issubset({"Active", "Inactive"}), "Unexpected status values!"

    df.to_csv(output_csv, index=False)
    elapsed = time.perf_counter() - t0
    return {
        "raw_rows": raw_rows,
        "clean_rows": len(df),
        "duplicates_removed": raw_rows - len(df),
        "preserved_nan": int(df["total_spend"].isna().sum()),
        "elapsed_sec": round(elapsed, 3),
        "guards_passed": "5/5",
    }


if __name__ == "__main__":
    messy = Path(__file__).parent / "messy_10k.csv"
    clean = Path(__file__).parent / "clean_10k.csv"
    generate_messy_csv(messy, 10_000)
    stats = inspect_fix_verify(messy, clean)
    print(f"Loaded messy_10k.csv ({stats['raw_rows']} rows)")
    print(f"Removed {stats['duplicates_removed']} duplicate customer_ids")
    print(f"Preserved {stats['preserved_nan']} financial NaNs (zero silent zero-fill)")
    print(f"Standardized 100% mixed dates & 14 country aliases")
    print(f"Schema assertions: {stats['guards_passed']} PASSED in {stats['elapsed_sec']}s")
