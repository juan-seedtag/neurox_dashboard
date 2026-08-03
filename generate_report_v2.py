#!/usr/bin/env python3
"""
NeuroX Demand Dashboard
=======================
Three-section, fully self-contained HTML report of NeuroX demand
(connection_type <> 'Reseller', Direct business lines excluded), quarterly:

  Tab 1  Commercial Activity — business_line × quarter pivot with
                               dsp_group_name × connection_type rows and
                               row/column totals (targets TBD).
  Tab 2  Deals Details       — DSP Overview, Deal Overview and Open Auction.
  Tab 3  Brand Details       — brand (adomain) × DSP group per quarter.

Global filters: DSP Group Name · Channel ID · Business Line.
Four Trino queries (commercial_activity / consolidated_deals / open_auction /
brands); all pivots are computed client-side. The output file needs no server
and can be shared (Drive, email) as-is.

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
from tools.report_generator_v2 import generate_html

# ── Paths / constants ────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = PROJECT_ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
LOGO_PATH = PROJECT_ROOT / "shared/assets/seedtag-isotype.png"
SQL_PATH = PROJECT_ROOT / "sql/consolidated_deals.sql"
OA_SQL_PATH = PROJECT_ROOT / "sql/open_auction.sql"
COM_SQL_PATH = PROJECT_ROOT / "sql/commercial_activity.sql"
BRANDS_SQL_PATH = PROJECT_ROOT / "sql/brands.sql"
# Crush Q3 (ported from notebooks/bfm_q3_blast — campaign dates are fixed in-SQL:
# baseline Jan 2025–Jun 2026, follow-up + new-deal activations from 2026-07-01)
CQ3_BASELINE_SQL = PROJECT_ROOT / "sql/crushq3_baseline_monthly.sql"
CQ3_FOLLOWUP_SQL = PROJECT_ROOT / "sql/crushq3_followup_monthly.sql"
CQ3_NEWDEALS_SQL = PROJECT_ROOT / "sql/crushq3_new_deals.sql"
CQ3_DAILY_SQL = PROJECT_ROOT / "sql/crushq3_daily_series.sql"

# adomain is not reliably populated before this date (brands query lower bound)
BRANDS_DATE_FROM = "2025-06-01"

# Tail trimming now happens in sql/brands.sql (per-group cumulative 90% revenue
# coverage). Set BRAND_TOP_N to an int to additionally cap embedded brands
# globally; None disables the Python-side trim.
BRAND_TOP_N = None

TODAY = date.today().isoformat()
NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Google Drive upload (reuses the sibling publisher_managers service account + shared drive)
DRIVE_SA_JSON = os.getenv("DRIVE_SA_JSON", "prj-jdpa-560863a21518.json")
DRIVE_ROOT_FOLDER_ID = os.getenv("DRIVE_ROOT_FOLDER_ID", "1TAFpUwZLeat4wNWPYeQGayLE56UMfBvl")
DRIVE_SUBFOLDER = os.getenv("DRIVE_SUBFOLDER", "Ad Exchange Dashboard")
DRIVE_FILENAME = os.getenv("DRIVE_FILENAME", "adex_dashboard_v2.html")


def default_date_from() -> str:
    """All of 2025 and 2026 — earlier quarters feed the QoQ variation math."""
    return "2025-01-01"


WINDOW_FIELDS = ("rev_qtd_current", "rev_qtd_prev_qtd", "rev_qtd_prev_year")


def _round_row(r: dict) -> None:
    """Normalise numeric fields in place (shared by Trino + CSV paths)."""
    r["rev_gross"] = round(float(r["rev_gross"] or 0), 2)
    r["impressions"] = int(float(r["impressions"] or 0))
    # outgoing_bids absent in pre-2026-08 CSVs → 0 (detail panel shows ·)
    r["outgoing_bids"] = int(float(r.get("outgoing_bids") or 0))
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


def _trim_brands(brand_rows: list[dict]) -> list[dict]:
    """Keep only rows of the BRAND_TOP_N adomains by total revenue (HTML embed)."""
    if BRAND_TOP_N is None:
        print(f"  ✓ brands: SQL 90%-coverage trim only ({len(brand_rows):,} rows embedded)")
        return brand_rows
    totals: dict[str, float] = {}
    for r in brand_rows:
        a = r.get("adomain") or "—"
        totals[a] = totals.get(a, 0.0) + float(r["rev_gross"] or 0)
    top = set(sorted(totals, key=totals.get, reverse=True)[:BRAND_TOP_N])
    kept = [r for r in brand_rows if (r.get("adomain") or "—") in top]
    print(f"  ✓ brands trimmed for embed: {len(totals):,} → {len(top):,} brands "
          f"({len(brand_rows):,} → {len(kept):,} rows)")
    return kept


def _round_rev(rows: list[dict]) -> None:
    """Round rev_gross in place (commercial / brand rows have no other numerics)."""
    for r in rows:
        r["rev_gross"] = round(float(r["rev_gross"] or 0), 2)


def _prep_crushq3(baseline: list[dict], followup: list[dict],
                  trk_deals: list[dict], trk_series: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """Normalise Crush Q3 rows for the embed.

    react_rows = baseline ∪ (followup months ≥ 2026-07 only) — the follow-up query
    also pulls H2-2025 as YoY bases, but the baseline already covers those months,
    so keeping them would double-count on merge.
    """
    fu = [r for r in followup if str(r["m"])[:7] >= "2026-07"]
    react = baseline + fu
    for r in react:
        r["m"] = str(r["m"])[:7]
        r["rev"] = round(float(r["rev"] or 0), 2)
    for r in trk_deals:
        for k in ("activation_date", "last_seen"):
            r[k] = str(r[k])[:10]
        r["revenue_since_activation"] = round(float(r["revenue_since_activation"] or 0), 2)
        r["active_days"] = int(r["active_days"] or 0)
    for r in trk_series:
        r["d"] = str(r["d"])[:10]
        r["rev"] = round(float(r["rev"] or 0), 2)
    return react, trk_deals, trk_series


def _render(rows: list[dict], oa_rows: list[dict], com_rows: list[dict],
            brand_rows: list[dict], react_rows: list[dict], trk_deals: list[dict],
            trk_series: list[dict], date_from: str, sql_texts: dict[str, str]) -> str:
    quarters = sorted({str(r["quarter"])[:10] for r in rows})
    advertisers = {r["advertiser"] for r in rows}
    print(f"  ✓ {len(quarters)} quarters ({quarters[0]} → {quarters[-1]}), "
          f"{len(advertisers):,} DSPs, {len(oa_rows):,} OA rows, "
          f"{len(com_rows):,} commercial rows, {len(brand_rows):,} brand rows, "
          f"{len(react_rows):,} reactivation rows, {len(trk_deals):,} new deals")
    logo_b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
    return generate_html(
        rows=rows,
        oa_rows=oa_rows,
        com_rows=com_rows,
        brand_rows=brand_rows,
        react_rows=react_rows,
        trk_deals=trk_deals,
        trk_series=trk_series,
        quarters=quarters,
        sql_texts=sql_texts,
        logo_b64=logo_b64,
        date_from=date_from,
        today=TODAY,
        now=NOW,
    )


def _sql_texts(date_from: str) -> dict[str, str]:
    """Representative SQL shown in the report's info tooltips."""
    return {
        "deals": SQL_PATH.read_text(encoding="utf-8").format(
            date_from=date_from, date_to=TODAY, build_date=TODAY),
        "open_auction": OA_SQL_PATH.read_text(encoding="utf-8").format(
            date_from=date_from, build_date=TODAY),
        "commercial": COM_SQL_PATH.read_text(encoding="utf-8").format(
            date_from=date_from, build_date=TODAY),
        "brands": BRANDS_SQL_PATH.read_text(encoding="utf-8").format(
            date_from=BRANDS_DATE_FROM, date_to=TODAY),
        "reactivation": (CQ3_BASELINE_SQL.read_text(encoding="utf-8")
                         + "\n\n-- ── follow-up months ──\n"
                         + CQ3_FOLLOWUP_SQL.read_text(encoding="utf-8")),
        "tracker": (CQ3_NEWDEALS_SQL.read_text(encoding="utf-8")
                    + "\n\n-- ── daily series ──\n"
                    + CQ3_DAILY_SQL.read_text(encoding="utf-8")),
    }


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
    print(f"NeuroX Demand Dashboard — {TODAY}")
    print(f"Data since: {date_from} (quarterly; brands since {BRANDS_DATE_FROM})\n")

    sql_template = SQL_PATH.read_text(encoding="utf-8")
    sql_oa = OA_SQL_PATH.read_text(encoding="utf-8").format(date_from=date_from, build_date=TODAY)
    sql_com = COM_SQL_PATH.read_text(encoding="utf-8").format(date_from=date_from, build_date=TODAY)
    brands_template = BRANDS_SQL_PATH.read_text(encoding="utf-8")

    # The heavy SSP-scan queries (deals + brands) run ONE QUARTER AT A TIME: a
    # single statement over the full range exceeds the Trino cluster memory limit
    # (~70 GB). Quarters are disjoint, so concatenating chunk results is exact.
    # Two chunks in flight at once keeps memory headroom; the light OA and
    # commercial (reporting_adex_demand) queries ride along in the same pool.
    chunks = _quarter_chunks(date_from, TODAY)
    brand_chunks = [(max(cf, BRANDS_DATE_FROM), ct)
                    for cf, ct in _quarter_chunks(BRANDS_DATE_FROM, TODAY)]
    print(f"Running commercial + open-auction queries + {len(chunks)} deals chunks "
          f"+ {len(brand_chunks)} brand chunks (2 in flight)…")
    from concurrent.futures import ThreadPoolExecutor
    rows: list[dict] = []
    brand_rows: list[dict] = []
    with ThreadPoolExecutor(max_workers=2) as ex:
        fut_com = ex.submit(run_trino_query, sql_com)
        fut_oa = ex.submit(run_trino_query, sql_oa)
        # Crush Q3 (all light — reporting_closing_bfm_demand only, dates fixed in-SQL)
        fut_cq3_base = ex.submit(run_trino_query, CQ3_BASELINE_SQL.read_text(encoding="utf-8"))
        fut_cq3_fu = ex.submit(run_trino_query, CQ3_FOLLOWUP_SQL.read_text(encoding="utf-8"))
        fut_cq3_new = ex.submit(run_trino_query, CQ3_NEWDEALS_SQL.read_text(encoding="utf-8"))
        fut_cq3_daily = ex.submit(run_trino_query, CQ3_DAILY_SQL.read_text(encoding="utf-8"))
        futs = {
            ex.submit(run_trino_query,
                      sql_template.format(date_from=cf, date_to=ct, build_date=TODAY)): cf
            for cf, ct in chunks
        }
        brand_futs = {
            ex.submit(run_trino_query,
                      brands_template.format(date_from=cf, date_to=ct)): cf
            for cf, ct in brand_chunks
        }
        com_rows = fut_com.result()
        print(f"  ✓ commercial activity: {len(com_rows):,} rows")
        oa_rows = fut_oa.result()
        print(f"  ✓ open auction: {len(oa_rows):,} ad_name×quarter rows")
        cq3_baseline = fut_cq3_base.result()
        cq3_followup = fut_cq3_fu.result()
        cq3_new = fut_cq3_new.result()
        cq3_daily = fut_cq3_daily.result()
        print(f"  ✓ crush q3: {len(cq3_baseline):,} baseline + {len(cq3_followup):,} follow-up rows, "
              f"{len(cq3_new):,} new deals, {len(cq3_daily):,} daily points")
        for fut in futs:
            chunk_rows = fut.result()  # raise on failure — a missing quarter is not acceptable
            rows.extend(chunk_rows)
            print(f"  ✓ deals {futs[fut]}: {len(chunk_rows):,} rows")
        for fut in brand_futs:
            chunk_rows = fut.result()
            brand_rows.extend(chunk_rows)
            print(f"  ✓ brands {brand_futs[fut]}: {len(chunk_rows):,} rows")
    print(f"  ✓ deals total: {len(rows):,} rows · brands total: {len(brand_rows):,} rows")

    for r in rows:
        _round_row(r)
    for r in oa_rows:
        r.setdefault("impressions", 0)
        _round_row(r)
    _round_rev(com_rows)
    _round_rev(brand_rows)

    # Stable names (used by --from-csv rebuilds) + dated copies for history.
    save_csv(rows, OUTPUT_DIR / "adex_deals.csv")
    save_csv(rows, OUTPUT_DIR / f"adex_deals_{TODAY}.csv")
    save_csv(oa_rows, OUTPUT_DIR / "adex_open_auction.csv")
    save_csv(oa_rows, OUTPUT_DIR / f"adex_open_auction_{TODAY}.csv")
    save_csv(com_rows, OUTPUT_DIR / "adex_commercial.csv")
    save_csv(com_rows, OUTPUT_DIR / f"adex_commercial_{TODAY}.csv")
    save_csv(brand_rows, OUTPUT_DIR / "adex_brands.csv")
    save_csv(brand_rows, OUTPUT_DIR / f"adex_brands_{TODAY}.csv")
    save_csv(cq3_baseline, OUTPUT_DIR / "adex_cq3_baseline.csv")
    save_csv(cq3_followup, OUTPUT_DIR / "adex_cq3_followup.csv")
    save_csv(cq3_new, OUTPUT_DIR / "adex_cq3_new_deals.csv")
    save_csv(cq3_daily, OUTPUT_DIR / "adex_cq3_daily.csv")
    print("  ✓ CSVs written to output/")

    react_rows, trk_deals, trk_series = _prep_crushq3(cq3_baseline, cq3_followup, cq3_new, cq3_daily)
    return _render(rows, oa_rows, com_rows, _trim_brands(brand_rows),
                   react_rows, trk_deals, trk_series,
                   date_from, _sql_texts(date_from))


def _load_simple_csv(csv_path: Path) -> list[dict]:
    """Load a commercial/brands CSV (quarter + dims + rev_gross only)."""
    import csv as _csv

    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in _csv.DictReader(f):
            r["rev_gross"] = round(float(r["rev_gross"] or 0), 2)
            r["quarter"] = str(r["quarter"])[:10]
            rows.append(r)
    return rows


def rebuild_from_csv(csv_path: Path, date_from: str) -> str:
    """Regenerate the HTML from cached CSVs — no Trino query (~instant).

    Note: the day-matched QTD window sums were computed at the CSVs' original build
    date; rebuild from CSV on the same day (layout iterations), re-query otherwise.
    """
    print(f"NeuroX Demand Dashboard — {TODAY} (rebuild from {csv_path.name})")
    rows = load_rows_from_csv(csv_path)
    oa_csv = OUTPUT_DIR / "adex_open_auction.csv"
    oa_rows = load_rows_from_csv(oa_csv) if oa_csv.exists() else []
    com_csv = OUTPUT_DIR / "adex_commercial.csv"
    com_rows = _load_simple_csv(com_csv) if com_csv.exists() else []
    brands_csv = OUTPUT_DIR / "adex_brands.csv"
    brand_rows = _load_simple_csv(brands_csv) if brands_csv.exists() else []

    def _raw_csv(name: str) -> list[dict]:
        import csv as _csv
        p = OUTPUT_DIR / name
        if not p.exists():
            return []
        with open(p, newline="", encoding="utf-8") as f:
            return list(_csv.DictReader(f))

    react_rows, trk_deals, trk_series = _prep_crushq3(
        _raw_csv("adex_cq3_baseline.csv"), _raw_csv("adex_cq3_followup.csv"),
        _raw_csv("adex_cq3_new_deals.csv"), _raw_csv("adex_cq3_daily.csv"))
    print(f"  ✓ {len(rows):,} deal rows, {len(oa_rows):,} OA rows, "
          f"{len(com_rows):,} commercial rows, {len(brand_rows):,} brand rows, "
          f"{len(react_rows):,} reactivation rows, {len(trk_deals):,} new deals loaded")
    return _render(rows, oa_rows, com_rows, _trim_brands(brand_rows),
                   react_rows, trk_deals, trk_series,
                   date_from, _sql_texts(date_from))


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
    ap = argparse.ArgumentParser(description="NeuroX Demand Dashboard")
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
    html_path = OUTPUT_DIR / "adex_dashboard_v2.html"

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
