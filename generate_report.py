#!/usr/bin/env python3
"""
Ad Exchange Deals Dashboard
===========================
Two-tab, fully self-contained HTML report of deal-based demand (Open Auction
excluded), aggregated by quarter:

  Tab 1  DSP Overview  — advertiser × quarter: revenue, # distinct deals,
                         avg spend per deal (rev_gross / distinct deals)
  Tab 2  Deal Overview — (clearvu_account, ad_name, deal_id) × quarter: rev_gross

One Trino query (sql/consolidated_deals.sql: Beachfront ∪ Seedtag SSP PMP) at
deal grain; both tabs pivot client-side. The output file needs no server and can
be shared (Drive, email) as-is.

Usage:
    uv run python generate_report.py                       # build
    uv run python generate_report.py --upload              # build + publish to Drive
    uv run python generate_report.py --from 2025-01-01
"""

from __future__ import annotations

import argparse
import base64
import os
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from tools._common import run_trino_query, save_csv
from tools.report_generator import generate_html

# ── Paths / constants ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
LOGO_PATH = PROJECT_ROOT / "shared/assets/seedtag-isotype.png"
SQL_PATH = PROJECT_ROOT / "sql/consolidated_deals.sql"
OA_SQL_PATH = PROJECT_ROOT / "sql/open_auction.sql"

TODAY = date.today().isoformat()
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Google Drive upload (reuses the sibling publisher_managers service account + shared drive)
DRIVE_SA_JSON = os.getenv("DRIVE_SA_JSON", "prj-jdpa-560863a21518.json")
DRIVE_ROOT_FOLDER_ID = os.getenv("DRIVE_ROOT_FOLDER_ID", "1TAFpUwZLeat4wNWPYeQGayLE56UMfBvl")
DRIVE_SUBFOLDER = os.getenv("DRIVE_SUBFOLDER", "Ad Exchange Dashboard")
DRIVE_FILENAME = os.getenv("DRIVE_FILENAME", "adex_dashboard.html")


def default_date_from() -> str:
    """All of 2025 and 2026 — earlier quarters feed the QoQ variation math."""
    return "2025-01-01"


WINDOW_FIELDS = ("rev_qtd_current", "rev_qtd_prev_qtd", "rev_qtd_prev_year")


def _round_row(r: dict) -> None:
    """Normalise numeric fields in place (shared by Trino + CSV paths)."""
    r["rev_gross"] = round(float(r["rev_gross"] or 0), 2)
    r["impressions"] = int(float(r["impressions"] or 0))
    for k in WINDOW_FIELDS:
        v = r.get(k)
        r[k] = round(float(v), 2) if v not in (None, "") else None


def load_rows_from_csv(csv_path: Path) -> list[dict]:
    """Load a previously saved CSV back into the row shape generate_html expects."""
    import csv as _csv

    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            r.setdefault("impressions", 0)
            _round_row(r)
            r["quarter"] = str(r["quarter"])[:10]
            for k in ("clearvu_account", "ad_name", "deal_id"):
                if r.get(k) == "":
                    r[k] = None
            rows.append(r)
    return rows


def _render(rows: list[dict], oa_rows: list[dict], date_from: str, sql: str) -> str:
    quarters = sorted({str(r["quarter"])[:10] for r in rows})
    advertisers = {r["advertiser"] for r in rows}
    print(f"  ✓ {len(quarters)} quarters ({quarters[0]} → {quarters[-1]}), "
          f"{len(advertisers):,} DSPs, {len(oa_rows):,} OA rows")
    logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return generate_html(
        rows=rows,
        oa_rows=oa_rows,
        quarters=quarters,
        sql_text=sql,
        logo_b64=logo_b64,
        date_from=date_from,
        today=TODAY,
        now=NOW,
    )


def _quarter_chunks(date_from: str, build_date: str) -> list[tuple[str, str]]:
    """[start, end) quarter windows covering date_from → build_date (inclusive)."""
    chunks = []
    d = date.fromisoformat(date_from)
    d = date(d.year, 3 * ((d.month - 1) // 3) + 1, 1)  # align to quarter start
    end = date.fromisoformat(build_date)
    while d <= end:
        months = d.year * 12 + (d.month - 1) + 3
        nxt = date(months // 12, months % 12 + 1, 1)
        chunks.append((d.isoformat(), nxt.isoformat()))
        d = nxt
    return chunks


def build_dashboard(date_from: str) -> str:
    print(f"Ad Exchange Deals Dashboard — {TODAY}")
    print(f"Deals since: {date_from} (quarterly)\n")

    sql_template = SQL_PATH.read_text(encoding="utf-8")
    sql_oa = OA_SQL_PATH.read_text(encoding="utf-8").format(date_from=date_from, build_date=TODAY)

    # The deals query runs ONE QUARTER AT A TIME: a single statement over the full
    # range exceeds the Trino cluster memory limit (~70 GB). Quarters are disjoint,
    # so concatenating chunk results is exact. Two chunks in flight at once keeps
    # memory headroom; the light OA query rides along in the same pool.
    chunks = _quarter_chunks(date_from, TODAY)
    print(f"Running open-auction query + {len(chunks)} quarterly deals chunks (2 in flight)…")
    from concurrent.futures import ThreadPoolExecutor
    rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_oa = ex.submit(run_trino_query, sql_oa)
        futs = {
            ex.submit(run_trino_query,
                      sql_template.format(date_from=cf, date_to=ct, build_date=TODAY)): cf
            for cf, ct in chunks
        }
        oa_rows = fut_oa.result()
        print(f"  ✓ open auction: {len(oa_rows):,} ad_name×quarter rows")
        for fut in futs:
            chunk_rows = fut.result()  # raise on failure — a missing quarter is not acceptable
            rows.extend(chunk_rows)
            print(f"  ✓ deals {futs[fut]}: {len(chunk_rows):,} rows")
    print(f"  ✓ deals total: {len(rows):,} deal×quarter rows")

    for r in rows:
        _round_row(r)
    for r in oa_rows:
        r.setdefault("impressions", 0)
        _round_row(r)

    # Stable names (used by --from-csv rebuilds) + dated copies for history.
    save_csv(rows, OUTPUT_DIR / "adex_deals.csv")
    save_csv(rows, OUTPUT_DIR / f"adex_deals_{TODAY}.csv")
    save_csv(oa_rows, OUTPUT_DIR / "adex_open_auction.csv")
    save_csv(oa_rows, OUTPUT_DIR / f"adex_open_auction_{TODAY}.csv")
    print("  ✓ CSVs written to output/")

    sql_repr = sql_template.format(date_from=date_from, date_to=TODAY, build_date=TODAY)
    return _render(rows, oa_rows, date_from, sql_repr)


def rebuild_from_csv(csv_path: Path, date_from: str) -> str:
    """Regenerate the HTML from cached CSVs — no Trino query (~instant).

    Note: the day-matched QTD window sums were computed at the CSVs' original build
    date; rebuild from CSV on the same day (layout iterations), re-query otherwise.
    """
    print(f"Ad Exchange Deals Dashboard — {TODAY} (rebuild from {csv_path.name})")
    rows = load_rows_from_csv(csv_path)
    oa_csv = OUTPUT_DIR / "adex_open_auction.csv"
    oa_rows = load_rows_from_csv(oa_csv) if oa_csv.exists() else []
    print(f"  ✓ {len(rows):,} deal rows, {len(oa_rows):,} OA rows loaded")
    sql = SQL_PATH.read_text(encoding="utf-8").format(date_from=date_from, date_to=TODAY, build_date=TODAY)
    return _render(rows, oa_rows, date_from, sql)


def upload_to_gdrive(html_path: Path) -> None:
    """Upload the self-contained HTML to Google Drive and print the share link."""
    from tools.drive_upload import upload_to_drive

    sa = PROJECT_ROOT / DRIVE_SA_JSON
    if not sa.exists():
        print(f"  ✗ Drive upload skipped — service account not found: {sa}")
        return
    print(f"\nUploading to Google Drive (folder '{DRIVE_SUBFOLDER}')…")
    try:
        url = upload_to_drive(
            service_account_json_path=str(sa),
            root_folder_id=DRIVE_ROOT_FOLDER_ID,
            subfolder_name=DRIVE_SUBFOLDER,
            filename=DRIVE_FILENAME,
            file_path=str(html_path),
        )
        print(f"  ✓ Shareable link: {url}")
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ Drive upload failed: {exc}")


def _default_deals_csv() -> Path:
    """Prefer the stable CSV; fall back to the newest dated one."""
    stable = OUTPUT_DIR / "adex_deals.csv"
    if stable.exists():
        return stable
    dated = sorted(OUTPUT_DIR.glob("adex_deals_*.csv"), key=lambda p: p.stat().st_mtime)
    if not dated:
        raise FileNotFoundError("No cached deals CSV in output/ — run a full build first.")
    return dated[-1]


def main() -> None:
    ap = argparse.ArgumentParser(description="Ad Exchange Deals Dashboard")
    ap.add_argument("--from", dest="date_from", default=default_date_from(),
                    help="include deals from this date (YYYY-MM-DD)")
    ap.add_argument("--no-build", action="store_true", help="reuse existing HTML (skip rebuild)")
    ap.add_argument("--from-csv", dest="from_csv", nargs="?", const="", default=None, metavar="PATH",
                    help="rebuild the HTML from a cached deals CSV instead of querying Trino "
                         "(default: output/adex_deals.csv, else newest output/adex_deals_*.csv)")
    ap.add_argument("--upload", action="store_true", help="upload the HTML to Google Drive")
    args = ap.parse_args()

    # Stable filename: matches the Drive name and means --no-build/--upload always
    # target the most recent build, never a stale date-suffixed artifact.
    html_path = OUTPUT_DIR / "adex_dashboard.html"

    if not args.no_build:
        if args.from_csv is not None:
            csv_path = Path(args.from_csv) if args.from_csv else _default_deals_csv()
            html = rebuild_from_csv(csv_path, args.date_from)
        else:
            html = build_dashboard(args.date_from)
        html_path.write_text(html, encoding="utf-8")
        size_mb = html_path.stat().st_size / 1e6
        print(f"\n✓ HTML saved: {html_path}  ({size_mb:.1f} MB)")

    if args.upload:
        upload_to_gdrive(html_path)
    else:
        print(f"  Self-contained file — open it directly or share it: {html_path}")


if __name__ == "__main__":
    main()
