#!/usr/bin/env python3
"""
Inspect → Fix → Verify Data Cleaning Pipeline
Cleans messy CSV exports with duplicate audit, null handling, date parsing, category normalization.
"""

import pandas as pd
import numpy as np
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

INPUT_CSV = Path("customers_messy.csv")
OUTPUT_CSV = Path("customers_clean.csv")
REPORT_MD = Path("cleaning_report.md")

COUNTRY_MAP = {
    'usa': 'United States', 'us': 'United States', 'united states': 'United States',
    'united states of america': 'United States', 'u.s.': 'United States', 'u.s.a.': 'United States',
    'uk': 'United Kingdom', 'united kingdom': 'United Kingdom', 'u.k.': 'United Kingdom',
    'great britain': 'United Kingdom', 'britain': 'United Kingdom',
    'deutschland': 'Germany', 'germany': 'Germany', 'de': 'Germany',
    'france': 'France', 'fr': 'France', 'french republic': 'France',
    'canada': 'Canada', 'ca': 'Canada',
    'australia': 'Australia', 'au': 'Australia', 'oz': 'Australia',
    'japan': 'Japan', 'jp': 'Japan', 'nippon': 'Japan',
    'brazil': 'Brazil', 'br': 'Brazil', 'brasil': 'Brazil',
    'india': 'India', 'in': 'India', 'bharat': 'India',
}

STATUS_MAP = {
    'active': 'Active', 'inactive': 'Inactive',
    'enabled': 'Active', 'disabled': 'Inactive',
    'true': 'Active', 'false': 'Inactive',
    '1': 'Active', '0': 'Inactive',
    'yes': 'Active', 'no': 'Inactive',
}

class CleaningReport:
    def __init__(self):
        self.steps: List[Dict[str, Any]] = []
        self.original_rows = 0

    def add_step(self, name: str, details: Dict[str, Any], rows_before: int, rows_after: int = None):
        self.steps.append({
            'name': name,
            'time': datetime.now().isoformat(),
            'details': details,
            'rows_before': rows_before,
            'rows_after': rows_after if rows_after is not None else rows_before,
        })

    def to_markdown(self) -> str:
        lines = [
            f"# Cleaning Report: {INPUT_CSV.name}",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Summary",
            f"- Original rows: {self.original_rows}",
            f"- Final rows: {self.steps[-1]['rows_after'] if self.steps else 0}",
            f"- Rows removed (duplicates): {self.original_rows - self.steps[-1]['rows_after'] if self.steps else 0}",
        ]
        spend_nulls = sum(1 for s in self.steps if s['name'] == 'Spend Cleanup' for d in [s['details']] if 'nulls' in str(d))
        lines.append(f"- Spend nulls remaining: {spend_nulls}")
        countries_mapped = sum(1 for s in self.steps if s['name'] == 'Country Normalization' for d in [s['details']] if 'Mapped' in str(d))
        lines.append(f"- Countries mapped to canonical: {countries_mapped}")
        lines.append(f"- All verification checks passed: {self._all_checks_passed()}")
        lines.append("")
        lines.append("## Step-by-Step Log")
        for step in self.steps:
            lines.append(f"### {step['name']}")
            lines.append(f"- Time: {step['time']}")
            for k, v in step['details'].items():
                lines.append(f"- {k}: {v}")
            lines.append(f"- Rows before: {step['rows_before']}")
            lines.append(f"- Rows after: {step['rows_after']}")
            lines.append("")
        return "\n".join(lines)

    def _all_checks_passed(self) -> bool:
        for step in self.steps:
            if step['name'] == 'Verification':
                return step['details'].get('All checks passed', False)
        return False


def normalize_phone(phone: str) -> str:
    if pd.isna(phone) or phone == '' or phone == '-':
        return ''
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 10:
        return f"+1-{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+1-{digits[1:4]}-{digits[4:7]}-{digits[7:]}"
    elif len(digits) >= 10:
        return f"+{digits}"
    return phone


def clean_data(df: pd.DataFrame, report: CleaningReport) -> pd.DataFrame:
    original_rows = len(df)
    report.original_rows = original_rows
    report.add_step('Load', {'Loaded': f'{original_rows} rows × {len(df.columns)} columns'}, original_rows)

    # Step 1: Duplicate Audit
    dup_mask = df.duplicated(subset=['customer_id'], keep=False)
    dup_count = int(dup_mask.sum())
    unique_dupes = int(df.loc[dup_mask, 'customer_id'].nunique()) if dup_count > 0 else 0
    report.add_step('Duplicate Audit', {
        'Found': f'{dup_count} rows with duplicate customer_ids ({unique_dupes} unique IDs affected)'
    }, original_rows)

    # Step 2: Deduplication
    df = df.drop_duplicates(subset=['customer_id'], keep='first')
    removed = original_rows - len(df)
    report.add_step('Deduplication', {
        'Removed': f'{removed} duplicate rows, kept first occurrence'
    }, original_rows, len(df))

    # Step 3: Spend Cleanup
    spend_col = 'total_spend'
    if spend_col in df.columns:
        null_before = int(df[spend_col].isna().sum())
        df[spend_col] = df[spend_col].replace({'-': np.nan, 'N/A': np.nan, 'n/a': np.nan, 'NA': np.nan})
        df[spend_col] = pd.to_numeric(df[spend_col], errors='coerce')
        null_after = int(df[spend_col].isna().sum())
        dashes_converted = null_after - null_before
        report.add_step('Spend Cleanup', {
            'Converted': f'{dashes_converted} dashes/N/A to NaN; nulls: {null_before} → {null_after}'
        }, len(df), len(df))

    # Step 4: Date Parsing
    date_cols = ['signup_date', 'last_purchase']
    for col in date_cols:
        if col in df.columns:
            null_before = int(df[col].isna().sum())
            df[col] = df[col].replace({'-': np.nan, 'N/A': np.nan, 'n/a': np.nan, 'NA': np.nan})
            df[col] = pd.to_datetime(df[col], format='mixed', dayfirst=False, errors='coerce')
            null_after = int(df[col].isna().sum())
            parsed = null_before - null_after if null_before > null_after else int(df[col].notna().sum())
            dashes = (df[col].isna().sum() - null_before) if null_after > null_before else 0
            report.add_step(f'Date Parse ({col})', {
                'Parsed': f'{parsed} dates; dashes→NaN: {max(0, int(dashes))}; unparseable→NaN: {max(0, null_after - null_before - int(dashes))}'
            }, len(df), len(df))

    # Step 5: Country Normalization
    if 'country' in df.columns:
        original_unique = df['country'].nunique()
        original_counts = df['country'].value_counts().to_dict()
        df['country_clean'] = df['country'].astype(str).str.strip().str.lower().map(COUNTRY_MAP)
        unmapped = df['country_clean'].isna().sum()
        df.loc[df['country_clean'].isna(), 'country_clean'] = df.loc[df['country_clean'].isna(), 'country']
        mapped_count = int(df['country_clean'].notna().sum())
        report.add_step('Country Normalization', {
            'Original unique countries': f'{original_unique} ({original_counts})',
            'Mapped': f'{mapped_count}',
            'Unmatched (preserved)': f'{int(unmapped)}'
        }, len(df), len(df))
        df['country'] = df['country_clean']
        df = df.drop(columns=['country_clean'])

    # Step 6: Phone Normalization
    if 'phone' in df.columns:
        df['phone'] = df['phone'].apply(normalize_phone)
        cleaned = int((df['phone'] != '').sum())
        report.add_step('Phone Normalization', {
            'Cleaned': f'{cleaned} phone numbers to E.164-like format'
        }, len(df), len(df))

    # Step 7: Status Cleanup
    if 'status' in df.columns:
        df['status'] = df['status'].astype(str).str.strip().str.lower().map(STATUS_MAP)
        report.add_step('Status Cleanup', {
            'Standardized': 'Active/Inactive casing'
        }, len(df), len(df))

    # Step 8: Verification
    checks = {
        'no_duplicate_ids': df['customer_id'].duplicated().sum() == 0,
        'spend_numeric': pd.api.types.is_numeric_dtype(df['total_spend']) if 'total_spend' in df.columns else True,
        'dates_parsed': df['signup_date'].notna().sum() > 0 if 'signup_date' in df.columns else True,
        'countries_mapped': df['country'].isin(COUNTRY_MAP.values()).sum() > 0 if 'country' in df.columns else True,
        'row_count_reasonable': 0.5 * original_rows <= len(df) <= original_rows,
    }
    all_passed = all(checks.values())
    report.add_step('Verification', {
        'All checks passed': all_passed,
        'Details': checks
    }, len(df), len(df))

    return df


def main():
    print("📥 Loading messy dataset...")
    df = pd.read_csv(INPUT_CSV)

    report = CleaningReport()
    print("🔄 Running cleaning pipeline...")
    df_clean = clean_data(df, report)

    print("💾 Exporting clean dataset...")
    df_clean.to_csv(OUTPUT_CSV, index=False)
    print(f"✅ Clean data saved: {OUTPUT_CSV} ({len(df_clean)} rows)")

    print("📄 Writing report...")
    REPORT_MD.write_text(report.to_markdown())
    print(f"✅ Report saved: {REPORT_MD}")

    print("\n🎉 Pipeline complete!")
    print(f"   Original: {report.original_rows} rows → Clean: {len(df_clean)} rows")
    print(f"   Duplicates removed: {report.original_rows - len(df_clean)}")


if __name__ == '__main__':
    main()