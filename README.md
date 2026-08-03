# Ad Exchange Deals Dashboard

Two-tab, fully self-contained HTML report of **deal-based demand** (Open Auction
excluded), by **quarter**. No server needed — open the file or share it (Drive, email).

- **Tab 1 — DSP Overview**: DSP (advertiser) × quarter, three sections:
  Revenue Gross (USD), Number of Deals (distinct ad names), Avg Spend per Deal
  (revenue ÷ distinct deals). Sorted by total revenue descending.
- **Tab 2 — Deal Overview**: ClearVu Account / Ad Name / Deal ID × quarter,
  revenue gross. Sorted by total revenue descending; searchable; paginated.

## Data

One Trino query — [sql/consolidated_deals.sql](sql/consolidated_deals.sql):

| Source | Scope | Notes |
|---|---|---|
| `analytics.bfm_demand` | `business_line <> 'Open Auction - BFM'` | Seat-based DSP resolution (Walmart / Bidswitch), `reporting_dsp_and_channel_mappings` normalisation |
| `analytics.stg_ssp_responses_daily` | PMP only (`product_type LIKE 'P%'`) | `bidder_dsp_mapping` + channel-based DSP resolution; `net_imp_paid / 1000` as rev_gross |

Returned at deal grain per quarter; both tabs pivot client-side in the browser.

## Setup

```bash
uv sync
```

Trino auth reuses `token.json` (Google OAuth) at the project root — same pattern as
the sibling analytics projects. If missing: `uv run python -m tools.trino_client --login`.

## Usage

```bash
uv run python generate_report.py                 # build → output/adex_dashboard_<date>.html
uv run python generate_report.py --upload        # build + publish to Google Drive (stable link)
uv run python generate_report.py --from 2025-01-01
```

Default window: the last 5 quarters (start of the quarter 4 quarters back → today).
The Drive upload upserts `adex_dashboard.html` in the "Ad Exchange Dashboard" folder
of the shared drive (service account: `prj-jdpa-…json`), so the share link stays stable.

## Layout

```
generate_report.py            Orchestrator (build + Drive upload)
tools/
  report_generator.py         Two-tab HTML/CSS/JS generation
  trino_client.py             Trino engine + Google-JWT auth (token.json)
  drive_upload.py             Drive upsert (from publisher_managers)
  _common.py                  run_trino_query, save_csv
sql/
  consolidated_deals.sql      The single source query (both tabs)
output/                       Generated HTML + CSV (git-ignored)
```
