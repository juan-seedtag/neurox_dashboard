"""Holistic Demand Dashboard generator — fully self-contained (no server).

Two top-level sections:

  🚀 Crush Q3 (ported from notebooks/bfm_q3_blast; campaign dates fixed in-SQL):
     Reactivation — Beachfront revenue-losing rows worst-first, per business line
                    (DSP Marketplace / Select - BFM / Open Auction). Loss = 2025
                    peak month vs Jun 2026, rows with 2025 peak >= $1k, excl.
                    PMP - Seedtag. Baseline Jan25-Jun26 + follow-up months with
                    prior-year (YoY) base columns.
     New Deals    — activations since Jul 1 2026 (first-ever appearance in the
                    Beachfront closing data) with daily-trend sparklines
                    ("tracker" in bfm_q3_blast). Extra embedded datasets:
                    REACT_ROWS / TRK_DEALS / TRK_SERIES (sql/crushq3_*.sql).

  🌍 Global Overview — the three original tabs:

  Tab 1  Commercial Activity — pivot: business_line × quarter columns,
                               dsp_group_name × connection_type rows,
                               revenue gross values, row + column totals.
                               (Targets not yet set — placeholder note.)
  Tab 2  Deals Details        — DSP Overview, ClearVu Account Overview (Select - BFM
                                only), Deal Overview and Open Auction
                               cards (deal-based demand, as before).
  Tab 3  Brand Details        — dsp_group_name × brand (adomain) rows,
                               quarter columns: which brands invest where.

Global filters (applied to every tab where the field exists):
  DSP Group Name · Channel ID · Business Line

All pivots are computed client-side from four embedded datasets:
  COM_ROWS   (sql/commercial_activity.sql — reporting_adex_demand)
  DEAL_ROWS  (sql/consolidated_deals.sql)
  OA_ROWS    (sql/open_auction.sql)
  BRAND_ROWS (sql/brands.sql)
Because filters cut at row level, every aggregate rebuilds on filter change.
"""

from __future__ import annotations

import json


def _pack(rows: list[dict]) -> str:
    """Columnar + dictionary encoding for the big embeds (deals/brands/react).

    List-of-dicts JSON repeats every key and every string per row; packing
    stores each column as an array and dictionary-encodes string columns
    (values once, rows as int indexes) — ~7x smaller, rebuilt into the same
    list of dicts at load time by the page's unpack() (lossless).
    """
    if not rows:
        return json.dumps({"n": 0, "d": {}, "c": {}})
    cols = list(rows[0].keys())
    dicts: dict[str, list] = {}
    data: dict[str, list] = {}
    for col in cols:
        # dates etc. → str, so fresh-Trino and --from-csv builds pack identically
        vals = [v if v is None or isinstance(v, (str, int, float, bool)) else str(v)
                for v in (r.get(col) for r in rows)]
        if all(v is None or isinstance(v, str) for v in vals):
            idx = {v: i for i, v in enumerate(dict.fromkeys(vals))}
            dicts[col] = list(idx)
            data[col] = [idx[v] for v in vals]
        else:
            data[col] = vals
    return json.dumps({"n": len(rows), "d": dicts, "c": data},
                      default=str, ensure_ascii=False)


def _logo_tag(b64: str, size: int) -> str:
    return f'<img src="data:image/png;base64,{b64}" alt="Seedtag" style="width:{size}px;height:{size}px">'


def generate_html(
    *,
    rows: list[dict],
    oa_rows: list[dict],
    com_rows: list[dict],
    brand_rows: list[dict],
    weekly_rows: list[dict],
    react_rows: list[dict],
    trk_deals: list[dict],
    trk_series: list[dict],
    quarters: list[str],
    sql_texts: dict[str, str],
    logo_b64: str,
    date_from: str,
    today: str,
    now: str,
) -> str:
    rows_json = _pack(rows)
    oa_json = json.dumps(oa_rows, default=str, ensure_ascii=False)
    com_json = json.dumps(com_rows, default=str, ensure_ascii=False)
    brand_json = _pack(brand_rows)
    weekly_json = json.dumps(weekly_rows, default=str, ensure_ascii=False)
    react_json = _pack(react_rows)
    trk_deals_json = json.dumps(trk_deals, default=str, ensure_ascii=False)
    trk_series_json = json.dumps(trk_series, default=str, ensure_ascii=False)
    quarters_json = json.dumps(quarters)
    sqls_json = json.dumps(sql_texts, ensure_ascii=False)
    logo32 = _logo_tag(logo_b64, 32)
    logo20 = _logo_tag(logo_b64, 20)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NeuroX Demand Dashboard — {today}</title>
<script>(function(){{var s=localStorage.getItem('seedtag-theme')||'auto';document.documentElement.setAttribute('data-theme',s);}})();</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#EBE6E4; --surface:#FFFFFF; --surface-2:#F7F4F2; --border:#D4D0CE;
  --text:#2F2E2E; --text-muted:#5E5C5B; --text-subtle:#8D8A89;
  --accent:#FF6B7C; --accent-ink:#FFFFFF; --kpi-strong:#000000; color-scheme:light;
}}
html[data-theme="dark"] {{
  --bg:#2F2E2E; --surface:#3D3B3A; --surface-2:#4A4847; --border:#5E5C5B;
  --text:#EBE6E4; --text-muted:#D4D0CE; --text-subtle:#8D8A89;
  --accent:#FF6B7C; --accent-ink:#2F2E2E; --kpi-strong:#FFFFFF; color-scheme:dark;
}}
@media (prefers-color-scheme: dark) {{
  html[data-theme="auto"] {{
    --bg:#2F2E2E;--surface:#3D3B3A;--surface-2:#4A4847;--border:#5E5C5B;
    --text:#EBE6E4;--text-muted:#D4D0CE;--text-subtle:#8D8A89;
    --accent-ink:#2F2E2E;--kpi-strong:#FFFFFF;color-scheme:dark;
  }}
}}
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:'Instrument Sans',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;font-size:14px;transition:background 200ms,color 200ms}}
h1{{font-family:'Instrument Serif',Georgia,serif;font-weight:400;letter-spacing:-0.01em}}
h2,h3,h4{{font-family:'Instrument Sans',sans-serif;font-weight:600}}

.report-header{{display:flex;align-items:center;gap:16px;padding:24px 32px;border-bottom:1px solid var(--border);background:var(--surface);position:relative}}
.report-header h1{{font-size:26px}}
.report-header .subtitle{{color:var(--text-subtle);font-size:13px;margin-top:3px}}
#updated-badge{{position:fixed;top:16px;right:60px;height:36px;display:inline-flex;align-items:center;gap:7px;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:18px;padding:0 14px;z-index:10000;box-shadow:0 2px 8px rgba(0,0,0,.08);font-size:12px;white-space:nowrap}}
#updated-badge .lbl{{font-size:10px;color:var(--text-subtle)}}
#updated-badge .val{{font-weight:600}}

#theme-toggle{{position:fixed;top:16px;right:16px;width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:50%;cursor:pointer;z-index:10000;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:transform 150ms}}
#theme-toggle:hover{{transform:scale(1.05)}}
#theme-toggle .icon-moon{{display:none}}
html[data-theme="dark"] #theme-toggle .icon-sun{{display:none}}
html[data-theme="dark"] #theme-toggle .icon-moon{{display:inline}}
@media(prefers-color-scheme:dark){{html[data-theme="auto"] #theme-toggle .icon-sun{{display:none}}html[data-theme="auto"] #theme-toggle .icon-moon{{display:inline}}}}

/* Global filters (apply to all tabs) */
.filter-slot{{margin-left:auto;display:flex;align-items:center;gap:14px;padding-bottom:8px;flex-wrap:wrap}}
.filter-item{{display:flex;align-items:center;gap:6px}}
.flabel{{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--text-subtle)}}
.ms-wrap{{position:relative}}
.ms-trigger{{display:flex;align-items:center;justify-content:space-between;gap:6px;padding:7px 10px;background:var(--surface);border:1px solid var(--border);border-radius:6px;cursor:pointer;height:32px;font-size:13px;color:var(--text);min-width:150px}}
.ms-trigger:hover,.ms-trigger.open{{border-color:var(--accent)}}
.ms-trigger .ms-label{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:170px}}
.ms-trigger .ms-arrow{{color:var(--text-subtle);font-size:10px;flex-shrink:0}}
.ms-trigger.active-filter{{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}}
.ms-dropdown{{display:none;position:absolute;top:calc(100% + 4px);right:0;min-width:260px;max-width:340px;background:var(--surface);border:1px solid var(--border);border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.15);z-index:10001;max-height:380px;flex-direction:column}}
.ms-dropdown.open{{display:flex}}
.ms-search{{padding:8px;border-bottom:1px solid var(--border)}}
.ms-search input{{width:100%;padding:6px 8px;background:var(--surface-2);border:1px solid var(--border);border-radius:5px;font-size:12px;color:var(--text);outline:none}}
.ms-options{{overflow-y:auto;padding:4px 0;flex:1}}
.ms-option{{display:flex;align-items:center;gap:8px;padding:6px 12px;cursor:pointer;font-size:13px}}
.ms-option:hover{{background:var(--surface-2)}}
.ms-option input{{accent-color:var(--accent);flex-shrink:0}}
.ms-option span{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.ms-footer{{padding:8px;border-top:1px solid var(--border);display:flex;justify-content:flex-end}}
.ms-footer button{{padding:5px 14px;background:transparent;color:var(--text-muted);border:1px solid var(--border);border-radius:5px;font-size:12px;cursor:pointer}}
.ms-footer button:hover{{border-color:var(--accent);color:var(--accent)}}

/* Tabs */
/* Section bar (Global Overview / Crush Q3) sits above the per-section tab bars */
.section-bar{{display:flex;gap:10px;padding:14px 32px 10px;background:var(--surface);align-items:center;flex-wrap:wrap}}
.section-btn{{border:1px solid var(--border);background:var(--surface-2);color:var(--text-muted);font-family:'Instrument Sans',sans-serif;font-size:15px;font-weight:700;padding:10px 26px;border-radius:10px;cursor:pointer}}
.section-btn:hover{{color:var(--text)}}
.section-btn.active{{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}}
.loss-pill{{display:inline-block;margin-left:8px;padding:2px 9px;border-radius:20px;font-size:11px;font-weight:700;background:#CF222E;color:#fff}}
.gain-pill{{background:#1A7F37}}
.sparkline{{vertical-align:middle}}
.tabs-bar{{display:flex;gap:4px;padding:14px 32px 0;background:var(--surface);border-bottom:1px solid var(--border);flex-wrap:wrap}}
.tab-btn{{border:1px solid var(--border);border-bottom:none;background:var(--surface-2);color:var(--text-muted);font-family:'Instrument Sans',sans-serif;font-size:14px;font-weight:600;padding:10px 22px;border-radius:10px 10px 0 0;cursor:pointer;position:relative;top:1px}}
.tab-btn:hover{{color:var(--text)}}
.tab-btn.active{{background:var(--bg);color:var(--text);border-color:var(--border)}}
.tab-panel{{display:none;padding:28px 32px}}
.tab-panel.active{{display:block}}
/* sub-tabs (inside a panel) */
.subtabs-bar{{display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap}}
.subtab-btn{{border:1px solid var(--border);background:var(--surface);color:var(--text-muted);font-family:'Instrument Sans',sans-serif;font-size:13px;font-weight:600;padding:7px 16px;border-radius:20px;cursor:pointer}}
.subtab-btn:hover{{color:var(--text);border-color:var(--accent)}}
.subtab-btn.active{{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}}
.subtab-panel{{display:none}}
.subtab-panel.active{{display:block}}

.section-title{{font-size:16px;font-weight:600;margin:26px 0 12px;display:flex;align-items:center;gap:8px}}
.section-title:first-child{{margin-top:0}}
.section-sub{{color:var(--text-subtle);font-size:13px;margin-bottom:14px}}

.card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:22px}}
.card-header{{display:flex;align-items:center;gap:8px;margin-bottom:14px;font-weight:600;font-size:14px;flex-wrap:wrap}}
.card-header .spacer{{flex:1}}
.info-icon{{width:20px;height:20px;background:#238636;color:#fff;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;cursor:pointer;flex-shrink:0;font-style:italic}}
.info-icon:hover{{opacity:.85}}
.btn-csv{{padding:6px 14px;background:var(--accent);color:var(--accent-ink);border:none;border-radius:6px;font-size:12px;cursor:pointer;font-weight:600}}
.btn-csv:hover{{opacity:.9}}
.note-banner{{background:var(--surface-2);border:1px dashed var(--border);border-radius:8px;padding:10px 14px;font-size:12px;color:var(--text-muted);margin-bottom:16px}}
.kpi-row{{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}}
.kpi-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 18px;min-width:200px;flex:1}}
.kpi-card .kpi-label{{font-size:12px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.04em}}
.kpi-card .kpi-value{{font-size:26px;font-weight:700;color:var(--kpi-strong);margin-top:2px;font-variant-numeric:tabular-nums}}
.kpi-card .kpi-sub{{font-size:12px;color:var(--text-subtle);margin-top:2px}}
.imp-row td{{color:var(--text-subtle);font-size:11px;border-bottom:1px solid var(--border)}}

/* expandable deal detail (Deals sub-tab) */
.deal-click{{cursor:pointer}}
.deal-click:hover td{{background:var(--surface)}}
.deal-chev{{display:inline-block;width:13px;color:var(--text-subtle);font-size:10px}}
.detail-row>td{{padding:0 8px 4px;border-bottom:1px solid var(--border)}}
.deal-detail{{position:sticky;left:8px;width:fit-content;max-width:940px;background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:10px 14px 12px;margin:4px 0 8px}}
.deal-detail-title{{font-size:12px;font-weight:600;margin-bottom:6px}}
.deal-detail table{{width:auto;border-collapse:collapse}}
.deal-detail th{{font-size:10px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.03em;padding:3px 10px;border-bottom:1px solid var(--border)}}
.deal-detail td{{font-size:12px;padding:4px 10px;font-variant-numeric:tabular-nums;border-bottom:none}}
.deal-detail-lbl{{color:var(--text-muted);font-weight:600;white-space:nowrap}}

.search-box{{padding:7px 12px;border:1px solid var(--border);background:var(--surface);color:var(--text);border-radius:6px;font-size:13px;min-width:230px;outline:none}}
.search-box:focus{{border-color:var(--accent)}}

.table-wrapper{{overflow-x:auto;border:1px solid var(--border);border-radius:10px}}
table{{width:100%;border-collapse:collapse;font-size:13px;background:var(--surface)}}
th{{text-align:left;padding:10px 14px;border-bottom:1px solid var(--border);font-weight:600;background:var(--surface-2);color:var(--text-muted);text-transform:uppercase;font-size:11px;letter-spacing:.04em;white-space:nowrap;position:sticky;top:0}}
td{{padding:9px 14px;border-bottom:1px solid var(--border);max-width:420px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
tr:last-child td{{border-bottom:none}}
tr:hover td{{background:var(--surface-2)}}
.number{{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}}
.muted{{color:var(--text-subtle)}}
tr.total-row td{{background:var(--surface-2);font-weight:700;border-top:2px solid var(--border)}}
tr.total-row:hover td{{background:var(--surface-2)}}
td.col-total,th.col-total{{font-weight:700}}

/* Frozen (sticky) identity columns */
td.sticky-col,th.sticky-col{{position:sticky;z-index:3;background:var(--surface)}}
th.sticky-col{{z-index:5;background:var(--surface-2)}}
tr:hover td.sticky-col{{background:var(--surface-2)}}
tr.total-row td.sticky-col{{background:var(--surface-2)}}
td.sticky-col,th.sticky-col{{box-shadow:2px 0 0 0 var(--border)}}
/* fixed widths so multi-column freezes line up */
.colw-dsp{{left:0;min-width:180px;max-width:180px}}
.colw-cv{{left:0;min-width:150px;max-width:150px}}
.colw-oa{{left:0;min-width:280px;max-width:280px}}
.colw-ad{{left:150px;min-width:240px;max-width:240px}}
.colw-id{{left:390px;min-width:135px;max-width:135px}}
.colw-com-dsp{{left:0;min-width:150px;max-width:150px}}
.colw-com-ct{{left:150px;min-width:110px;max-width:110px}}
.colw-com-prod{{left:260px;min-width:120px;max-width:120px}}
tr.grp-total td{{background:var(--surface-2);font-weight:700;border-top:1px dashed var(--border)}}
tr.grp-total td.sticky-col{{background:var(--surface-2)}}
tr.grp-total:hover td{{background:var(--surface-2)}}
td.pacing,th.pacing{{font-style:italic}}
.colw-br-dsp{{left:0;min-width:170px;max-width:170px}}
.colw-br-brand{{left:170px;min-width:190px;max-width:190px}}
/* grouped header */
th.grp{{text-align:center;font-size:12px;letter-spacing:.03em;border-left:2px solid var(--border)}}
th.grp-start,td.grp-start{{border-left:2px solid var(--border)}}
th.pair-start,td.pair-start{{border-left:1px solid var(--border)}}
th.grp-click{{cursor:pointer;user-select:none}}
th.grp-click:hover{{color:var(--accent)}}
td.collapsed-cell{{text-align:center;color:var(--text-subtle)}}
.pos{{color:#1A7F37;font-weight:600}}
.neg{{color:#CF222E;font-weight:600}}
html[data-theme="dark"] .pos{{color:#57AB5A}}
html[data-theme="dark"] .neg{{color:#F47067}}

.table-meta{{display:flex;align-items:center;justify-content:space-between;margin:14px 2px 0;flex-wrap:wrap;gap:8px}}
.table-meta .count{{font-size:13px;color:var(--text-subtle)}}
.pagination{{display:flex;align-items:center;gap:6px}}
.pagination button{{padding:4px 10px;background:var(--surface);border:1px solid var(--border);border-radius:5px;font-size:12px;cursor:pointer;color:var(--text)}}
.pagination button:hover{{border-color:var(--accent)}}
.pagination button.active{{background:var(--accent);color:var(--accent-ink);border-color:var(--accent)}}
.pagination button:disabled{{opacity:.4;cursor:default}}
.pagination .pg-info{{font-size:12px;color:var(--text-subtle)}}

.badge-internal{{background:var(--accent);color:#fff;font-size:11px;font-weight:600;padding:3px 9px;border-radius:20px;text-transform:uppercase;letter-spacing:.04em}}

.tooltip{{display:none;position:absolute;background:var(--surface);border:1px solid var(--border);padding:12px;border-radius:8px;z-index:9999;font-size:12px;max-width:620px;max-height:420px;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word;box-shadow:0 8px 24px rgba(0,0,0,.15);margin-top:6px;line-height:1.5}}
.tooltip.active{{display:block}}
.tooltip .copy-hint{{display:block;margin-top:8px;color:var(--text-subtle);font-family:'Instrument Sans',sans-serif;font-size:11px}}

footer.report-footer{{padding:16px 32px;color:var(--text-subtle);font-size:12px;display:flex;align-items:center;gap:8px}}
footer.report-footer img{{opacity:.75}}

@media (max-width:768px){{
  .tab-panel{{padding:18px 16px}} .report-header{{padding:16px}} .tabs-bar{{padding:10px 16px 0}}
  .search-box{{min-width:100%}}
}}
</style>
</head>
<body>

<button id="theme-toggle" aria-label="Toggle dark mode">
  <svg class="icon-sun" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41"/></svg>
  <svg class="icon-moon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
</button>

<header class="report-header">
  {logo32}
  <div>
    <h1>NeuroX Demand Dashboard</h1>
    <div class="subtitle">Analytics Team &middot; Revenue Gross (USD) &middot; NeuroX scope (no Reseller, no Direct business lines) &middot; quarterly</div>
  </div>
</header>

<div id="updated-badge" title="Last data refresh">🕐 <span class="lbl">Last updated</span> <span class="val">{now}</span></div>

<!-- Section bar: the two top-level areas of the holistic dashboard -->
<div class="section-bar">
  <button class="section-btn active" data-section="global" onclick="showSection('global')">🌍 Global Overview</button>
  <button class="section-btn" data-section="crush" onclick="showSection('crush')">🚀 Crush Q3</button>
  <div class="filter-slot" id="filter-slot"></div>
</div>

<div class="tabs-bar" id="tabbar-global">
  <button class="tab-btn active" data-tab="com" onclick="showTab('com')">📈 Commercial Activity</button>
  <button class="tab-btn" data-tab="deals" onclick="showTab('deals')">🎯 Deals Details</button>
  <button class="tab-btn" data-tab="brand" onclick="showTab('brand')">🏢 Brand Details</button>
  <button class="tab-btn" data-tab="wk" onclick="showTab('wk')">📅 Weekly View</button>
</div>
<div class="tabs-bar" id="tabbar-crush" style="display:none">
  <button class="tab-btn" data-tab="react" onclick="showTab('react')">♻️ Reactivation</button>
  <button class="tab-btn" data-tab="trk" onclick="showTab('trk')">🆕 New Deals</button>
</div>

<!-- ── Tab 1: Commercial Activity ── -->
<div class="tab-panel active" id="panel-com">
  <div class="section-sub">General overview of NeuroX demand — revenue gross by business line and quarter, split by DSP group and connection type.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-com')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-com"></div>
  </div>
  <div class="note-banner">🎯 Targets and expected behavior will be added here once targets are set.</div>
  <div class="card">
    <div class="card-header">📈 Revenue Gross — Business Line × Quarter
      <span class="muted" style="font-weight:400">— rows: DSP × Connection × Product · totals for rows and columns · current quarter shown as pacing</span>
      <div class="spacer"></div><button class="btn-csv" id="com-merge-btn" onclick="comToggleMerge()" title="Merge Open Auction (Seedtag+BFM), PMP (DSP Marketplace + PMP Web/CTV O&amp;O) and Curation (Select + Curation) into single columns">🔗 Merged BLs: ON</button><button class="btn-csv" onclick="comCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="com-head"></thead><tbody id="com-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="com-count"></span><div class="pagination" id="com-pag"></div></div>
  </div>
</div>

<!-- ── Tab 2: Deals Details ── -->
<div class="tab-panel" id="panel-deals">
  <div class="section-sub">Deal-based demand (Open Auction in its own sub-tab). Sorted by total revenue.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-deals')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-deals"></div>
  </div>

  <div class="subtabs-bar">
    <button class="subtab-btn active" data-subtab="dsp" onclick="showSubTab('dsp')">📊 DSP Overview</button>
    <button class="subtab-btn" data-subtab="cva" onclick="showSubTab('cva')">🏛️ ClearVu Account Overview</button>
    <button class="subtab-btn" data-subtab="deal" onclick="showSubTab('deal')">🎯 Deals</button>
    <button class="subtab-btn" data-subtab="oa" onclick="showSubTab('oa')">🏷️ Open Auction</button>
  </div>

  <div class="subtab-panel active" id="subpanel-dsp">
  <div class="card">
    <div class="card-header">📊 DSP Performance by Quarter
      <span class="muted" style="font-weight:400">— 🧾 Number of Deals · 💰 Revenue · ⚖️ Avg Spend per Deal</span>
      <div class="spacer"></div><button class="btn-csv" onclick="ovCSV('dsp')">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="dsp-head"></thead><tbody id="dsp-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="dsp-count"></span><div class="pagination" id="dsp-pag"></div></div>
  </div>
  </div>

  <div class="subtab-panel" id="subpanel-cva">
  <div class="card">
    <div class="card-header">🏛️ ClearVu Account Performance by Quarter <span class="badge-internal">Internal</span>
      <span class="muted" style="font-weight:400">— Select - BFM only · 🧾 Number of Deals · 💰 Revenue · ⚖️ Avg Spend per Deal</span>
      <div class="spacer"></div><button class="btn-csv" onclick="ovCSV('cva')">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="cva-head"></thead><tbody id="cva-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="cva-count"></span><div class="pagination" id="cva-pag"></div></div>
  </div>
  </div>

  <div class="subtab-panel" id="subpanel-deal">
  <div class="card">
    <div class="card-header">🎯 Deals <span class="badge-internal">Internal</span>
      <div class="spacer"></div>
      <input class="search-box" id="deal-search" placeholder="Search account / ad name / deal ID…" oninput="dealSearch(this.value)">
      <button class="btn-csv" onclick="dealCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="deal-head"></thead><tbody id="deal-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="deal-count"></span><div class="pagination" id="deal-pag"></div></div>
  </div>
  </div>

  <div class="subtab-panel" id="subpanel-oa">
  <div class="card">
    <div class="card-header">🏷️ Open Auction (Beachfront, by ad name) <span class="badge-internal">Internal</span>
      <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-oa')" style="vertical-align:-5px">i</span>
      <div class="tooltip" id="sql-tip-oa"></div>
      <div class="spacer"></div>
      <input class="search-box" id="oa-search" placeholder="Search ad name…" oninput="oaSearch(this.value)">
      <button class="btn-csv" onclick="oaCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="oa-head"></thead><tbody id="oa-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="oa-count"></span><div class="pagination" id="oa-pag"></div></div>
  </div>
  </div>
</div>

<!-- ── Tab 3: Brand Details ── -->
<div class="tab-panel" id="panel-brand">
  <div class="section-sub">Which brands are investing where — revenue gross by brand (adomain) per quarter, one DSP group at a time (pick it below). Data starts June 2025. Top brands by total revenue (long tail in output/adex_brands.csv). Sorted by total revenue.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-brand')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-brand"></div>
  </div>
  <div class="card">
    <div class="card-header">🏢 Brands <span class="badge-internal">Internal</span>
      <span class="flabel" style="margin-left:8px">DSP</span>
      <select class="search-box" id="brand-dsp-select" style="min-width:200px" onchange="brandDspPick(this.value)"></select>
      <div class="spacer"></div>
      <input class="search-box" id="brand-search" placeholder="Search brand…" oninput="brandSearch(this.value)">
      <button class="btn-csv" onclick="brandCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="brand-head"></thead><tbody id="brand-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="brand-count"></span><div class="pagination" id="brand-pag"></div></div>
  </div>
</div>

<!-- ── Tab 4: Weekly View ── -->
<div class="tab-panel" id="panel-wk">
  <div class="section-sub" id="wk-sub">Week-over-week revenue — rolling 7-day windows anchored on the build date.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-wk')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-wk"></div>
  </div>
  <div class="card">
    <div class="card-header">📅 Weekly Revenue — WoW
      <span class="flabel" style="margin-left:8px">Group by</span>
      <button class="subtab-btn wk-dim active" data-dim="bl" onclick="wkDimToggle('bl')">Business Line</button>
      <button class="subtab-btn wk-dim" data-dim="ct" onclick="wkDimToggle('ct')">Connection Type</button>
      <button class="subtab-btn wk-dim" data-dim="pf" onclick="wkDimToggle('pf')">Product Format</button>
      <div class="spacer"></div>
      <button class="btn-csv" onclick="wkCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="wk-head"></thead><tbody id="wk-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="wk-count"></span><div class="pagination" id="wk-pag"></div></div>
  </div>
</div>

<!-- ── Crush Q3 · Reactivation ── -->
<div class="tab-panel" id="panel-react">
  <div class="section-sub">Q3 reactivation targets — Beachfront revenue-losing rows, worst first.
    Loss = 2025 peak month vs Jun 2026 · rows with 2025 peak ≥ $1k · excl. PMP - Seedtag.
    Baseline Jan 2025 – Jun 2026; follow-up months appear after the separator with their prior-year (YoY) base underneath.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-react')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-react"></div>
  </div>

  <div class="subtabs-bar">
    <button class="subtab-btn react-bl active" data-bl="DSP Marketplace - BFM" onclick="showReactBL('DSP Marketplace - BFM')">DSP Marketplace<span id="pill-dspm"></span></button>
    <button class="subtab-btn react-bl" data-bl="Select - BFM" onclick="showReactBL('Select - BFM')">Select - BFM<span id="pill-select"></span></button>
    <button class="subtab-btn react-bl" data-bl="Open Auction - BFM" onclick="showReactBL('Open Auction - BFM')">Open Auction<span id="pill-oa"></span></button>
  </div>

  <div class="card">
    <div class="card-header">♻️ <span id="react-title">Reactivation targets</span> <span class="badge-internal">Internal</span>
      <span class="flabel" style="margin-left:12px">Segments</span>
      <button class="subtab-btn seg-react active" data-seg="dsp" onclick="reactSegToggle('dsp')">DSP</button>
      <button class="subtab-btn seg-react active" data-seg="cva" onclick="reactSegToggle('cva')">ClearVu Account</button>
      <button class="subtab-btn seg-react active" data-seg="ad" onclick="reactSegToggle('ad')">Ad Name</button>
      <div class="spacer"></div>
      <input class="search-box" id="react-search" placeholder="Search DSP / account / ad name / deal ID…" oninput="reactSearch(this.value)">
      <button class="btn-csv" onclick="reactCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="react-head"></thead><tbody id="react-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="react-count"></span><div class="pagination" id="react-pag"></div></div>
  </div>
</div>

<!-- ── Crush Q3 · New Deals (tracker) ── -->
<div class="tab-panel" id="panel-trk">
  <div class="section-sub">New deal activations — a deal counts as new on the first date it ever appears in Beachfront closing data (history starts Jan 2025); tracking activations since Jul 1 2026. Sorted by revenue since activation.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-trk')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-trk"></div>
  </div>
  <div class="kpi-row" id="trk-kpis"></div>
  <div class="card">
    <div class="card-header">🆕 New deals <span class="badge-internal">Internal</span>
      <span class="flabel" style="margin-left:8px">Activation month</span>
      <select class="search-box" id="trk-month-select" style="min-width:140px" onchange="trkMonthPick(this.value)"></select>
      <span class="muted" id="trk-data-end" style="font-weight:400"></span>
      <span class="flabel" style="margin-left:12px">Segments</span>
      <button class="subtab-btn seg-trk active" data-seg="dsp" onclick="trkSegToggle('dsp')">DSP</button>
      <button class="subtab-btn seg-trk active" data-seg="cva" onclick="trkSegToggle('cva')">ClearVu Account</button>
      <button class="subtab-btn seg-trk active" data-seg="ad" onclick="trkSegToggle('ad')">Ad Name</button>
      <div class="spacer"></div>
      <input class="search-box" id="trk-search" placeholder="Search deal / DSP / account…" oninput="trkSearch(this.value)">
      <button class="btn-csv" onclick="trkCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="trk-head"></thead><tbody id="trk-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="trk-count"></span><div class="pagination" id="trk-pag"></div></div>
  </div>
</div>

<footer class="report-footer">
  {logo20}
  Analytics Team &middot; Demand Dashboard &middot; {today}
</footer>

<script>
// unpack: columnar + dictionary payload → list of row objects (see _pack in the generator)
function unpack(p){{
  const cols=Object.keys(p.c), out=new Array(p.n);
  for(let i=0;i<p.n;i++){{
    const o={{}};
    for(const c of cols){{ const v=p.c[c][i]; o[c]=p.d[c]?p.d[c][v]:v; }}
    out[i]=o;
  }}
  return out;
}}
const DEAL_ROWS = unpack({rows_json});
const OA_ROWS = {oa_json};
const COM_ROWS = {com_json};
const BRAND_ROWS = unpack({brand_json});
const WK_ROWS = {weekly_json};        // Weekly View · {{period, dims, rev_gross}}
const REACT_ROWS = unpack({react_json});       // Crush Q3 · monthly rows {{m,bl,dsp,cva,ad,did,rev}}
const TRK_DEALS = {trk_deals_json};    // Crush Q3 · new-deal activations
const TRK_SERIES = {trk_series_json};  // Crush Q3 · daily revenue per new deal
const QUARTERS = {quarters_json};   // sorted ISO quarter-start dates (deals range)
const SQL_TEXTS = {sqls_json};

// ── helpers ──
const fmtUSD  = n => '$' + (Number(n)||0).toLocaleString('en-US',{{maximumFractionDigits:0}});
const fmtUSD2 = n => '$' + (Number(n)||0).toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
const fmtUSDc = n => '$' + Intl.NumberFormat('en-US',{{notation:'compact',maximumFractionDigits:1}}).format(Number(n)||0);
const fmtInt  = n => (Number(n)||0).toLocaleString('en-US');
function fmtQ(iso){{ const d=new Date(String(iso).slice(0,10)); return d.getUTCFullYear()+' Q'+(Math.floor(d.getUTCMonth()/3)+1); }}
function escapeHtml(s){{return String(s??'').replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));}}
const qOf = r => String(r.quarter).slice(0,10);

// Per-dataset quarter lists (commercial starts 2025-01, brands 2025-06)
const COM_QUARTERS = [...new Set(COM_ROWS.map(qOf))].sort();
const BRAND_QUARTERS = [...new Set(BRAND_ROWS.map(qOf))].sort();

// theme
document.getElementById('theme-toggle').addEventListener('click',()=>{{
  const h=document.documentElement, cur=h.getAttribute('data-theme')||'auto';
  const next=cur==='auto'?'light':cur==='light'?'dark':'auto';
  h.setAttribute('data-theme',next); localStorage.setItem('seedtag-theme',next);
}});

// SQL tooltips (one SQL text per section)
const SQL_TIPS = {{'sql-tip-com':'commercial','sql-tip-deals':'deals','sql-tip-oa':'open_auction','sql-tip-brand':'brands','sql-tip-wk':'weekly','sql-tip-react':'reactivation','sql-tip-trk':'tracker'}};
Object.entries(SQL_TIPS).forEach(([id,key])=>{{
  const t=document.getElementById(id), txt=SQL_TEXTS[key]||'';
  t.innerHTML=escapeHtml(txt)+'<span class="copy-hint">Click to copy</span>';
  t.addEventListener('click',()=>{{
    navigator.clipboard&&navigator.clipboard.writeText(txt);
    const h=t.querySelector('.copy-hint'); if(h){{const o=h.textContent;h.textContent='Copied ✓';setTimeout(()=>h.textContent=o,1200);}}
  }});
}});
function toggleTooltip(e,id){{
  e.stopPropagation();
  const t=document.getElementById(id);
  document.querySelectorAll('.tooltip.active').forEach(x=>{{if(x!==t)x.classList.remove('active');}});
  t.classList.toggle('active');
}}
document.addEventListener('click',()=>document.querySelectorAll('.tooltip.active').forEach(t=>t.classList.remove('active')));

// sections (Global Overview / Crush Q3) — each remembers its last active tab
const SECTION_TABS = {{global:['com','deals','brand','wk'], crush:['react','trk']}};
const sectionLastTab = {{global:'com', crush:'react'}};
let currentSection='global';
function showSection(sec){{
  currentSection=sec;
  document.querySelectorAll('.section-btn').forEach(b=>b.classList.toggle('active',b.dataset.section===sec));
  document.getElementById('tabbar-global').style.display = sec==='global'?'flex':'none';
  document.getElementById('tabbar-crush').style.display = sec==='crush'?'flex':'none';
  showTab(sectionLastTab[sec]);
}}
// tabs
function showTab(name){{
  Object.entries(SECTION_TABS).forEach(([sec,tabs])=>{{ if(tabs.includes(name)) sectionLastTab[sec]=name; }});
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('active',p.id==='panel-'+name));
}}
// sub-tabs inside Deals Details (scoped — Reactivation has its own BL buttons)
function showSubTab(name){{
  document.querySelectorAll('#panel-deals .subtab-btn').forEach(b=>b.classList.toggle('active',b.dataset.subtab===name));
  document.querySelectorAll('#panel-deals .subtab-panel').forEach(p=>p.classList.toggle('active',p.id==='subpanel-'+name));
}}

// pagination helper
function renderPagination(elId,pages,cur,go){{
  const el=document.getElementById(elId);
  if(pages<=1){{el.innerHTML='';return;}}
  const range=[];const delta=2;
  for(let i=Math.max(1,cur-delta);i<=Math.min(pages,cur+delta);i++)range.push(i);
  if(range[0]>1)range.unshift(1); if(range[range.length-1]<pages)range.push(pages);
  let html=`<button ${{cur===1?'disabled':''}} data-p="${{cur-1}}">←</button>`;
  let last=0;
  range.forEach(p=>{{ if(p-last>1)html+=`<span class="pg-info">…</span>`; html+=`<button class="${{p===cur?'active':''}}" data-p="${{p}}">${{p}}</button>`; last=p; }});
  html+=`<button ${{cur===pages?'disabled':''}} data-p="${{cur+1}}">→</button><span class="pg-info">${{cur}} / ${{pages}}</span>`;
  el.innerHTML=html;
  el.querySelectorAll('button[data-p]').forEach(b=>b.onclick=()=>{{const p=+b.dataset.p; if(p>=1&&p<=pages)go(p);}});
}}
function downloadCSV(matrix,name){{
  const esc=v=>{{ if(v==null)return''; const s=String(v); return /[",\\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s; }};
  const csv=matrix.map(r=>r.map(esc).join(',')).join('\\n');
  const blob=new Blob([csv],{{type:'text/csv;charset=utf-8;'}});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name+'.csv';
  document.body.appendChild(a); a.click(); a.remove();
}}

// ══════════════ Global filters: DSP Group · Channel ID · Business Line ══════════════
// Option universes come from the union of all datasets; each dataset is
// filtered row-level on the fields it actually carries (missing field = pass).
const FILTERS = [
  {{key:'dsp',     label:'DSP Group',     all:'All DSPs',           fields:{{com:'dsp_group_name', deal:'advertiser', oa:'advertiser', brand:'dsp_group_name', wk:'dsp_group_name', react:'dsp', trk:'dsp_group_name'}} }},
  {{key:'channel', label:'Channel ID',    all:'All Channels',       fields:{{com:'channel_id', deal:'channel_id', brand:'channel_id', wk:'channel_id'}} }},
  {{key:'bl',      label:'Business Line', all:'All Business Lines', fields:{{com:'business_line', deal:'business_line', brand:'business_line', wk:'business_line', react:'bl', trk:'business_line'}} }},
];
const selected = {{dsp:new Set(), channel:new Set(), bl:new Set()}};

// Options per filter, sorted by total revenue desc across all datasets.
FILTERS.forEach(f=>{{
  const rev=new Map();
  const add=(rows,field)=>{{ if(!field)return; rows.forEach(r=>{{ const v=r[field]; if(v!=null&&v!=='') rev.set(v,(rev.get(v)||0)+(Number(r.rev_gross)||0)); }}); }};
  add(COM_ROWS,f.fields.com); add(DEAL_ROWS,f.fields.deal); add(OA_ROWS,f.fields.oa); add(BRAND_ROWS,f.fields.brand);
  const addRev=(rows,field,revField)=>{{ if(!field)return; rows.forEach(r=>{{ const v=r[field]; if(v!=null&&v!==''&&v!=='—') rev.set(v,(rev.get(v)||0)+(Number(r[revField])||0)); }}); }};
  addRev(REACT_ROWS,f.fields.react,'rev'); addRev(TRK_DEALS,f.fields.trk,'revenue_since_activation');
  f.options=[...rev.entries()].sort((a,b)=>b[1]-a[1]).map(e=>e[0]);
}});

function rowPass(r,ds){{
  return FILTERS.every(f=>{{
    const sel=selected[f.key]; if(sel.size===0) return true;
    const field=f.fields[ds]; if(!field) return true;          // dataset lacks the field
    const v=r[field]; if(v==null||v==='') return false;
    return sel.has(v);
  }});
}}
const filt = (rows,ds) => rows.filter(r=>rowPass(r,ds));

// Multiselect UI (generic)
function buildFilters(){{
  document.getElementById('filter-slot').innerHTML = FILTERS.map(f=>`
    <div class="filter-item">
      <span class="flabel">${{f.label}}</span>
      <div class="ms-wrap">
        <div class="ms-trigger" id="ms-trig-${{f.key}}" onclick="msToggle('${{f.key}}',event)">
          <span class="ms-label" id="ms-label-${{f.key}}">${{f.all}}</span><span class="ms-arrow">▼</span>
        </div>
        <div class="ms-dropdown" id="ms-dd-${{f.key}}">
          <div class="ms-search"><input type="text" placeholder="Search…" oninput="msSearch('${{f.key}}',this.value)"></div>
          <div class="ms-options" id="ms-opts-${{f.key}}"></div>
          <div class="ms-footer"><button onclick="msClear('${{f.key}}')">Clear</button></div>
        </div>
      </div>
    </div>`).join('');
  FILTERS.forEach(f=>buildOptions(f.key));
}}
function buildOptions(key){{
  const f=FILTERS.find(x=>x.key===key);
  document.getElementById('ms-opts-'+key).innerHTML = f.options.map(v=>
    `<label class="ms-option" data-val="${{escapeHtml(v)}}">
       <input type="checkbox" ${{selected[key].has(v)?'checked':''}} onchange="msPick('${{key}}','${{encodeURIComponent(v)}}',this.checked)">
       <span title="${{escapeHtml(v)}}">${{escapeHtml(v)}}</span>
     </label>`).join('');
}}
function msToggle(key,e){{
  e&&e.stopPropagation();
  FILTERS.forEach(f=>{{ if(f.key!==key){{
    document.getElementById('ms-dd-'+f.key).classList.remove('open');
    document.getElementById('ms-trig-'+f.key).classList.remove('open');
  }} }});
  document.getElementById('ms-dd-'+key).classList.toggle('open');
  document.getElementById('ms-trig-'+key).classList.toggle('open');
}}
document.addEventListener('click',e=>{{ if(!e.target.closest('.ms-wrap')) FILTERS.forEach(f=>{{
  document.getElementById('ms-dd-'+f.key).classList.remove('open');
  document.getElementById('ms-trig-'+f.key).classList.remove('open');
}}); }});
function msSearch(key,q){{
  q=q.toLowerCase();
  document.querySelectorAll(`#ms-opts-${{key}} .ms-option`).forEach(o=>{{
    o.style.display=(!q||o.dataset.val.toLowerCase().includes(q))?'':'none';
  }});
}}
function msPick(key,enc,on){{
  const v=decodeURIComponent(enc);
  if(on) selected[key].add(v); else selected[key].delete(v);
  applyFilters();
}}
function msClear(key){{
  selected[key].clear(); buildOptions(key);
  const inp=document.querySelector(`#ms-dd-${{key}} .ms-search input`); if(inp){{inp.value='';msSearch(key,'');}}
  applyFilters();
}}
function applyFilters(){{
  FILTERS.forEach(f=>{{
    const sel=selected[f.key];
    document.getElementById('ms-label-'+f.key).textContent =
      sel.size===0?f.all:(sel.size===1?[...sel][0]:sel.size+' selected');
    document.getElementById('ms-trig-'+f.key).classList.toggle('active-filter',sel.size>0);
  }});
  comPage=dealPage=oaPage=brandPage=wkPage=reactPage=trkPage=1;
  OVERVIEWS.forEach(o=>o.page=1);
  rebuildAll();
}}
const anyFilter=()=>FILTERS.some(f=>selected[f.key].size>0);

// ══════════════ Tab 1: Commercial Activity pivot ══════════════
// columns: business_line × quarter (current partial quarter labelled "Current Q
// pacing", italic) + row Total; rows: dsp × connection × product, grouped with a
// TOTAL row per dsp × connection block + bottom grand-total row.
// Rebuilt from filtered COM_ROWS. Pagination is per GROUP (block stays whole).
let COM_BLS=[], COM_GROUPS=[], COM_TOTAL=null, COM_PROD_TOTALS=[];
const comQPartial=q=>!qComplete(q);   // current quarter → pacing column
// Optional business-line merge for the pivot columns (toggle in the card header).
// Display-only: the global Business Line filter keeps operating on raw values.
let comMerge=true;
const COM_BL_MERGE={{
  'Open Auction - Seedtag':'Open Auction','Open Auction - BFM':'Open Auction',
  'DSP Marketplace - BFM':'PMP','PMP Web - O&O':'PMP','PMP CTV - O&O':'PMP',
  'Select - BFM':'Curation','PMP - Curation':'Curation'
}};
const comBL=r=>comMerge?(COM_BL_MERGE[r.business_line]||r.business_line):r.business_line;
// Every entity carries both metrics: revenue (cells/total) and impressions
// (cellsI/totalI) — rendered as paired rows, revenue on top.
const fmtImpc=n=>Intl.NumberFormat('en-US',{{notation:'compact',maximumFractionDigits:1}}).format(Number(n)||0);
function comToggleMerge(){{
  comMerge=!comMerge;
  document.getElementById('com-merge-btn').textContent='🔗 Merged BLs: '+(comMerge?'ON':'OFF');
  buildCom(); renderCom();
}}
function buildCom(){{
  const rows=filt(COM_ROWS,'com');
  const blRev=new Map();
  rows.forEach(r=>blRev.set(comBL(r),(blRev.get(comBL(r))||0)+(Number(r.rev_gross)||0)));
  COM_BLS=[...blRev.entries()].sort((a,b)=>b[1]-a[1]).map(e=>e[0]);
  // group = dsp × connection; leaf rows = product
  const gmap=new Map();
  rows.forEach(r=>{{
    const gkey=(r.dsp_group_name??'—')+'\\u0001'+(r.connection_type??'—');
    let g=gmap.get(gkey);
    if(!g){{g={{dsp:r.dsp_group_name??'—',ct:r.connection_type??'—',prods:new Map(),cells:{{}},cellsI:{{}},total:0,totalI:0}};gmap.set(gkey,g);}}
    const p=r.product_category??'Other';
    let e=g.prods.get(p); if(!e){{e={{product:p,cells:{{}},cellsI:{{}},total:0,totalI:0}};g.prods.set(p,e);}}
    const ck=comBL(r)+'\\u0001'+qOf(r), v=Number(r.rev_gross)||0, vi=Number(r.impressions)||0;
    e.cells[ck]=(e.cells[ck]||0)+v; e.total+=v; e.cellsI[ck]=(e.cellsI[ck]||0)+vi; e.totalI+=vi;
    g.cells[ck]=(g.cells[ck]||0)+v; g.total+=v; g.cellsI[ck]=(g.cellsI[ck]||0)+vi; g.totalI+=vi;
  }});
  COM_GROUPS=[...gmap.values()];
  COM_GROUPS.forEach(g=>{{
    g.rows=[...g.prods.values()].sort((a,b)=>b.total-a.total);
    delete g.prods;
  }});
  // sort: DSPs by their overall total desc, then connections inside by total desc
  const dspTot=new Map();
  COM_GROUPS.forEach(g=>dspTot.set(g.dsp,(dspTot.get(g.dsp)||0)+g.total));
  COM_GROUPS.sort((a,b)=>(dspTot.get(b.dsp)-dspTot.get(a.dsp))||(a.dsp>b.dsp?1:a.dsp<b.dsp?-1:b.total-a.total));
  COM_TOTAL={{cells:{{}},cellsI:{{}},total:0,totalI:0}};
  COM_GROUPS.forEach(g=>{{ COM_TOTAL.total+=g.total; COM_TOTAL.totalI+=g.totalI;
    Object.entries(g.cells).forEach(([k,v])=>COM_TOTAL.cells[k]=(COM_TOTAL.cells[k]||0)+v);
    Object.entries(g.cellsI).forEach(([k,v])=>COM_TOTAL.cellsI[k]=(COM_TOTAL.cellsI[k]||0)+v); }});
  // column totals per product category (across ALL DSPs / connections)
  const pmap=new Map();
  rows.forEach(r=>{{
    const p=r.product_category??'Other';
    let e=pmap.get(p); if(!e){{e={{product:p,cells:{{}},cellsI:{{}},total:0,totalI:0}};pmap.set(p,e);}}
    const ck=comBL(r)+'\\u0001'+qOf(r), v=Number(r.rev_gross)||0, vi=Number(r.impressions)||0;
    e.cells[ck]=(e.cells[ck]||0)+v; e.total+=v; e.cellsI[ck]=(e.cellsI[ck]||0)+vi; e.totalI+=vi;
  }});
  COM_PROD_TOTALS=[...pmap.values()].sort((a,b)=>b.total-a.total);
}}
const COM_PAGE=8;   // dsp × connection groups per page
let comPage=1;
function comQLabel(q){{ return comQPartial(q)?'Current Q pacing':fmtQ(q); }}
function comQTitle(q){{ return comQPartial(q)?`${{fmtQ(q)}} quarter-to-date (partial)`:''; }}
function comCells(cells,isImp){{
  return COM_BLS.map(bl=>COM_QUARTERS.map((q,i)=>{{
    const v=cells[bl+'\\u0001'+q];
    const cls='number'+(i===0?' grp-start':'')+(comQPartial(q)?' pacing':'');
    return v!=null?`<td class="${{cls}}" title="${{isImp?fmtInt(v):fmtUSD2(v)}}">${{isImp?fmtImpc(v):fmtUSDc(v)}}</td>`
                  :`<td class="${{cls}} muted">·</td>`;
  }}).join('')).join('');
}}
function renderCom(){{
  // header row 1: business line groups; row 2: quarters (+ pacing label)
  let h='<tr><th rowspan="2" class="sticky-col colw-com-dsp" style="vertical-align:bottom">DSP</th>'+
        '<th rowspan="2" class="sticky-col colw-com-ct" style="vertical-align:bottom">Connection</th>'+
        '<th rowspan="2" class="sticky-col colw-com-prod" style="vertical-align:bottom">Product</th>'+
    COM_BLS.map(bl=>`<th class="grp" colspan="${{COM_QUARTERS.length}}">${{escapeHtml(bl)}}</th>`).join('')+
    '<th rowspan="2" class="number grp col-total" style="vertical-align:bottom">Total</th></tr>';
  h+='<tr>'+COM_BLS.map(bl=>COM_QUARTERS.map((q,i)=>
    `<th class="number${{i===0?' grp-start':''}}${{comQPartial(q)?' pacing':''}}" title="${{comQTitle(q)}}">${{comQLabel(q)}}</th>`
  ).join('')).join('')+'</tr>';
  document.getElementById('com-head').innerHTML=h;

  const pages=Math.max(1,Math.ceil(COM_GROUPS.length/COM_PAGE));
  comPage=Math.min(comPage,pages);
  const start=(comPage-1)*COM_PAGE, slice=COM_GROUPS.slice(start,start+COM_PAGE);
  const comPair=(cls,c1,c2,c3,e)=>
      `<tr${{cls?` class="${{cls}}"`:''}}><td class="sticky-col colw-com-dsp" title="${{escapeHtml(c1)}}">${{c1}}</td>`+
      `<td class="sticky-col colw-com-ct">${{c2}}</td>`+
      `<td class="sticky-col colw-com-prod" title="${{escapeHtml(c3)}}">${{c3}}</td>`+
      comCells(e.cells,false)+
      `<td class="number col-total grp-start" title="${{fmtUSD2(e.total)}}">${{fmtUSD(e.total)}}</td></tr>`+
      `<tr class="imp-row${{cls?' '+cls:''}}"><td class="sticky-col colw-com-dsp"></td>`+
      `<td class="sticky-col colw-com-ct"></td>`+
      `<td class="sticky-col colw-com-prod">↳ impressions</td>`+
      comCells(e.cellsI,true)+
      `<td class="number col-total grp-start" title="${{fmtInt(e.totalI)}}">${{fmtImpc(e.totalI)}}</td></tr>`;
  let body=slice.map(g=>{{
    const rows=g.rows.map((e,j)=>
      comPair('',j===0?escapeHtml(g.dsp):'<span class="muted">〃</span>',
                 j===0?escapeHtml(g.ct):'<span class="muted">〃</span>',
                 escapeHtml(e.product),e)).join('');
    // per-group TOTAL row (only when the group has >1 product row)
    const tot=g.rows.length>1?comPair('grp-total',escapeHtml(g.dsp),escapeHtml(g.ct),'TOTAL',g):'';
    return rows+tot;
  }}).join('');
  // column-totals block (over ALL filtered groups, not just current page):
  // one Total row per product category, then the grand TOTAL row
  if(COM_GROUPS.length){{
    body+=COM_PROD_TOTALS.map((e,j)=>
      comPair('grp-total',j===0?'Total':'<span class="muted">〃</span>','All',escapeHtml(e.product),e)).join('');
    body+=comPair('total-row','Total','All','TOTAL',COM_TOTAL);
  }}
  document.getElementById('com-body').innerHTML = body || '<tr><td class="muted">No data</td></tr>';
  document.getElementById('com-count').textContent =
    `${{fmtInt(COM_GROUPS.length)}} DSP × connection groups · ${{fmtUSD(COM_TOTAL?COM_TOTAL.total:0)}} · ${{fmtImpc(COM_TOTAL?COM_TOTAL.totalI:0)}} impressions${{anyFilter()?' (filtered)':''}}`;
  renderPagination('com-pag',pages,comPage,p=>{{comPage=p;renderCom();}});
}}
function comCSV(){{
  const header=['DSP','Connection Type','Product','Metric'];
  COM_BLS.forEach(bl=>COM_QUARTERS.forEach(q=>header.push(`${{bl}} ${{comQLabel(q)}}`)));
  header.push('Total');
  const rowOf=(dsp,ct,prod,metric,cells,total)=>{{
    const row=[dsp,ct,prod,metric];
    COM_BLS.forEach(bl=>COM_QUARTERS.forEach(q=>{{
      const v=cells[bl+'\\u0001'+q];
      row.push(v!=null?Math.round(v*100)/100:0);
    }}));
    row.push(Math.round(total*100)/100);
    return row;
  }};
  const both=(dsp,ct,prod,e)=>{{
    body.push(rowOf(dsp,ct,prod,'revenue',e.cells,e.total));
    body.push(rowOf(dsp,ct,prod,'impressions',e.cellsI,e.totalI));
  }};
  const body=[];
  COM_GROUPS.forEach(g=>{{
    g.rows.forEach(e=>both(g.dsp,g.ct,e.product,e));
    if(g.rows.length>1) both(g.dsp,g.ct,'TOTAL',g);
  }});
  COM_PROD_TOTALS.forEach(e=>both('Total','All',e.product,e));
  if(COM_TOTAL) both('Total','All','TOTAL',COM_TOTAL);
  downloadCSV([header,...body],'neurox_commercial_activity');
}}

// ══════════════ Tab 2: Deals Details ══════════════
// A quarter is "complete" once the next quarter has started (relative to build date).
const BUILD_TS = Date.parse({json.dumps(today)});
function qComplete(q){{
  const d=new Date(String(q).slice(0,10));
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth()+3, 1) <= BUILD_TS;
}}
const fmtPct = v => (v>=0?'+':'−') + Math.abs(v*100).toFixed(1) + '%';
const fmtUSDdelta = v => (v>=0?'+':'−') + fmtUSDc(Math.abs(v));

// Days of the current quarter that are complete (window size used by the SQL build).
const QTD_DAYS = (()=>{{
  const d=new Date(BUILD_TS);
  const qs=Date.UTC(d.getUTCFullYear(), 3*Math.floor(d.getUTCMonth()/3), 1);
  return Math.round((BUILD_TS-qs)/86400000);
}})();

function prevYearQ(q){{ const d=new Date(q); return `${{d.getUTCFullYear()-1}}-${{String(q).slice(5,10)}}`; }}
const CMP_QOQ = QUARTERS.slice(1).map((q,j)=>{{
  const partial=!qComplete(q);
  return {{q, prev:QUARTERS[j], kind:'qoq', partial,
          label:fmtQ(q)+' vs '+fmtQ(QUARTERS[j])+(partial?' · QTD':'')}};
}});
const CMP_YOY = QUARTERS.filter(q=>QUARTERS.includes(prevYearQ(q))).map(q=>{{
  const partial=!qComplete(q);
  return {{q, prev:prevYearQ(q), kind:'yoy', partial,
          label:fmtQ(q)+' vs '+fmtQ(prevYearQ(q))+(partial?' · QTD':'')}};
}});
function cmpVals(e,c){{
  let cur, prev;
  if(c.partial){{ cur=e.qtdCur; prev=(c.kind==='qoq')?e.qtdPrevQ:e.qtdPrevY; }}
  else {{ cur=e.rev[c.q]; prev=e.rev[c.prev]; }}
  if(prev==null||prev===0||cur==null) return null;
  return {{pct:cur/prev-1, usd:cur-prev}};
}}
const addN=(a,b)=> b==null ? a : (a==null ? b : a+b);   // null-preserving sum

// ══════════════ Overview tables — one builder, two instances ══════════════
// Identical structure and metrics; the instances differ only in the grouping
// dimension and, for ClearVu, a hard business-line scope:
//   dsp → advertiser,       all business lines
//   cva → clearvu_account,  business_line = 'Select - BFM' only. ClearVu accounts
//         exist only on that line (the SSP branch of consolidated_deals.sql sets
//         clearvu_account NULL), so scoping is what makes the table meaningful.
// The scope is applied ON TOP of the global filters, so excluding Select - BFM in
// the Business Line filter legitimately empties this table (message says so).
const CVA_BL='Select - BFM';
const OV_PAGE=25;
const ovLbl=v=>(v==null||v===''||v==='nan')?'—':v;
const OVERVIEWS=[
  {{key:'dsp', dimOf:r=>ovLbl(r.advertiser), colLabel:'DSP (Advertiser)', unit:'DSPs',
    colw:'colw-dsp', csvName:'neurox_dsp_overview'}},
  {{key:'cva', dimOf:r=>ovLbl(r.clearvu_account), colLabel:'ClearVu Account', unit:'ClearVu Accounts',
    colw:'colw-cv', csvName:'neurox_clearvu_overview',
    scope:r=>r.business_line===CVA_BL,
    emptyMsg:'No <b>'+CVA_BL+'</b> rows in the current selection — check the Business Line filter.'}},
];
OVERVIEWS.forEach(o=>{{ o.list=[]; o.page=1; o.collapsed={{qoq:true, yoy:true}}; }});
const OV=Object.fromEntries(OVERVIEWS.map(o=>[o.key,o]));

function ovBuild(o){{
  const map=new Map();
  const rows=o.scope?filt(DEAL_ROWS,'deal').filter(o.scope):filt(DEAL_ROWS,'deal');
  rows.forEach(r=>{{
    const a=o.dimOf(r);
    let e=map.get(a); if(!e){{e={{dim:a,rev:{{}},deals:{{}},revTotal:0,dealSetAll:new Set(),qtdCur:null,qtdPrevQ:null,qtdPrevY:null}};map.set(a,e);}}
    const q=qOf(r);
    const v=Number(r.rev_gross)||0;
    e.rev[q]=(e.rev[q]||0)+v; e.revTotal+=v;
    e.qtdCur=addN(e.qtdCur, r.rev_qtd_current!=null?Number(r.rev_qtd_current):null);
    e.qtdPrevQ=addN(e.qtdPrevQ, r.rev_qtd_prev_qtd!=null?Number(r.rev_qtd_prev_qtd):null);
    e.qtdPrevY=addN(e.qtdPrevY, r.rev_qtd_prev_year!=null?Number(r.rev_qtd_prev_year):null);
    if(r.ad_name!=null){{ (e.deals[q]=e.deals[q]||new Set()).add(r.ad_name); e.dealSetAll.add(r.ad_name); }}
  }});
  const list=[...map.values()].sort((a,b)=>b.revTotal-a.revTotal);
  list.forEach(e=>{{
    e.nDeals={{}}; QUARTERS.forEach(q=>{{ e.nDeals[q]=e.deals[q]?e.deals[q].size:0; }});
    e.nDealsTotal=e.dealSetAll.size;
    e.avg={{}}; QUARTERS.forEach(q=>{{ e.avg[q]=e.nDeals[q]?(e.rev[q]||0)/e.nDeals[q]:null; }});
    e.avgTotal=e.nDealsTotal?e.revTotal/e.nDealsTotal:null;
    delete e.deals; delete e.dealSetAll;
  }});
  o.list=list;
}}

const SECTIONS=[
  {{key:'deals', label:'🧾 Number of Deals',
    cell:(e,q)=>e.nDeals[q]?fmtInt(e.nDeals[q]):null, title:(e,q)=>'',
    csv:(e,q)=>e.nDeals[q]||0}},
  {{key:'revenue', label:'💰 Revenue Gross (USD)',
    cell:(e,q)=>e.rev[q]!=null?fmtUSDc(e.rev[q]):null, title:(e,q)=>e.rev[q]!=null?fmtUSD2(e.rev[q]):'',
    csv:(e,q)=>e.rev[q]??0}},
  {{key:'avg', label:'⚖️ Avg Spend per Deal',
    cell:(e,q)=>e.avg[q]!=null?fmtUSDc(e.avg[q]):null, title:(e,q)=>e.avg[q]!=null?fmtUSD2(e.avg[q]):'',
    csv:(e,q)=>e.avg[q]!=null?Math.round(e.avg[q]*100)/100:''}},
  {{key:'qoq', label:'📊 QoQ Variation', cmps:CMP_QOQ, collapsible:true}},
  {{key:'yoy', label:'📅 YoY Variation', cmps:CMP_YOY, collapsible:true}},
];
function ovToggleSection(key,sec){{ const o=OV[key]; o.collapsed[sec]=!o.collapsed[sec]; ovRender(o); }}
function cmpTitle(c){{ return c.partial?`Day-matched: first ${{QTD_DAYS}} completed days of each quarter`:''; }}

function ovRender(o){{
  const nQ=QUARTERS.length;
  const coll=s=>s.collapsible&&o.collapsed[s.key];
  const width=s=>{{
    if(coll(s)) return 1;
    return s.cmps ? s.cmps.length*2 : nQ;
  }};
  let h=`<tr><th rowspan="3" class="sticky-col ${{o.colw}}" style="vertical-align:bottom">${{o.colLabel}}</th>`+
    SECTIONS.map(s=>{{
      const cls='grp'+(s.collapsible?' grp-click':'');
      const attrs=s.collapsible?` onclick="ovToggleSection('${{o.key}}','${{s.key}}')" title="Click to ${{coll(s)?'expand':'collapse'}}"`:'';
      const arrow=s.collapsible?(coll(s)?' ▸':' ▾'):'';
      return `<th class="${{cls}}" colspan="${{width(s)}}"${{attrs}}>${{s.label}}${{arrow}}</th>`;
    }}).join('')+'</tr>';
  h+='<tr>'+SECTIONS.map(s=>{{
    if(coll(s)) return '<th class="grp-start" rowspan="2"></th>';
    if(s.cmps) return s.cmps.map((c,i)=>`<th class="number${{i===0?' grp-start':' pair-start'}}" colspan="2" title="${{cmpTitle(c)}}">${{c.label}}</th>`).join('');
    return QUARTERS.map((q,i)=>`<th class="number${{i===0?' grp-start':''}}" rowspan="2">${{fmtQ(q)}}</th>`).join('');
  }}).join('')+'</tr>';
  h+='<tr>'+SECTIONS.map(s=>{{
    if(!s.cmps||o.collapsed[s.key]) return '';
    return s.cmps.map((c,i)=>`<th class="number${{i===0?' grp-start':' pair-start'}}">%</th><th class="number">USD</th>`).join('');
  }}).join('')+'</tr>';
  document.getElementById(o.key+'-head').innerHTML=h;

  const LIST=o.list;
  const pages=Math.max(1,Math.ceil(LIST.length/OV_PAGE));
  o.page=Math.min(o.page,pages);
  const start=(o.page-1)*OV_PAGE, slice=LIST.slice(start,start+OV_PAGE);
  document.getElementById(o.key+'-body').innerHTML = slice.map(e=>
    `<tr><td class="sticky-col ${{o.colw}}" title="${{escapeHtml(e.dim)}}">${{escapeHtml(e.dim)}}</td>`+
    SECTIONS.map(s=>{{
      if(coll(s)) return '<td class="collapsed-cell grp-start">⋯</td>';
      if(s.cmps) return s.cmps.map((c,i)=>{{
        const v=cmpVals(e,c);
        const first=i===0?' grp-start':' pair-start';
        if(!v) return `<td class="number${{first}}"><span class="muted">·</span></td><td class="number"><span class="muted">·</span></td>`;
        const sign=v.pct>=0?' pos':' neg';
        return `<td class="number${{first}}${{sign}}" title="${{cmpTitle(c)}}">${{fmtPct(v.pct)}}</td>`+
               `<td class="number${{sign}}" title="${{fmtUSD2(v.usd)}}">${{fmtUSDdelta(v.usd)}}</td>`;
      }}).join('');
      return QUARTERS.map((q,i)=>{{
        const v=s.cell(e,q);
        return `<td class="number${{i===0?' grp-start':''}}"${{s.title(e,q)?` title="${{s.title(e,q)}}"`:''}}>${{v!=null?v:'<span class="muted">·</span>'}}</td>`;
      }}).join('');
    }}).join('')+'</tr>').join('')
    || `<tr><td class="muted" colspan="99">${{o.emptyMsg||'No data'}}</td></tr>`;
  document.getElementById(o.key+'-count').textContent =
    `${{fmtInt(LIST.length)}} ${{o.unit}} · sorted by total revenue${{anyFilter()?' (filtered)':''}}`;
  renderPagination(o.key+'-pag',pages,o.page,p=>{{o.page=p;ovRender(o);}});
}}
function ovCSV(key){{
  const o=OV[key];
  const header=[o.colLabel];
  SECTIONS.forEach(s=>{{
    const name=s.label.replace(/^[^ ]+ /,'');
    if(s.cmps) s.cmps.forEach(c=>{{ header.push(`${{name}} ${{c.label}} %`, `${{name}} ${{c.label}} USD`); }});
    else QUARTERS.forEach(q=>header.push(`${{name}} ${{fmtQ(q)}}`));
  }});
  const body=o.list.map(e=>{{
    const row=[e.dim];
    SECTIONS.forEach(s=>{{
      if(s.cmps) s.cmps.forEach(c=>{{
        const v=cmpVals(e,c);
        row.push(v?(v.pct*100).toFixed(1)+'%':'', v?Math.round(v.usd*100)/100:'');
      }});
      else QUARTERS.forEach(q=>row.push(s.csv(e,q)));
    }});
    return row;
  }});
  downloadCSV([header,...body],o.csvName);
}}

// ── Deal pivot — rebuilt from FILTERED deal rows ──
let DEALS=[];
function buildDeals(){{
  const map=new Map();
  filt(DEAL_ROWS,'deal').forEach(r=>{{
    const key=[r.clearvu_account??'',r.ad_name??'',r.deal_id??''].join('\\u0001');
    let e=map.get(key);
    if(!e){{e={{clearvu:r.clearvu_account,ad_name:r.ad_name,deal_id:r.deal_id,advertiser:r.advertiser,rev:{{}},imp:{{}},bid:{{}},total:0,totalI:0,totalB:0,qtdCur:null,qtdPrevQ:null,qtdPrevY:null}};map.set(key,e);}}
    const q=qOf(r);
    const v=Number(r.rev_gross)||0, vi=Number(r.impressions)||0, vb=Number(r.outgoing_bids)||0;
    e.rev[q]=(e.rev[q]||0)+v; e.total+=v;
    e.imp[q]=(e.imp[q]||0)+vi; e.totalI+=vi;
    e.bid[q]=(e.bid[q]||0)+vb; e.totalB+=vb;
    e.qtdCur=addN(e.qtdCur, r.rev_qtd_current!=null?Number(r.rev_qtd_current):null);
    e.qtdPrevQ=addN(e.qtdPrevQ, r.rev_qtd_prev_qtd!=null?Number(r.rev_qtd_prev_qtd):null);
    e.qtdPrevY=addN(e.qtdPrevY, r.rev_qtd_prev_year!=null?Number(r.rev_qtd_prev_year):null);
  }});
  DEALS=[...map.values()].sort((a,b)=>b.total-a.total);
  DEALS.forEach((e,i)=>e._i=i);   // stable handle for the detail panel (valid until next build)
  dealOpen=null;                  // any rebuild collapses the open panel
}}
function dealGrowth(e,prevKey){{
  const prev=e[prevKey];
  if(prev==null||prev===0||e.qtdCur==null) return null;
  return e.qtdCur/prev-1;
}}
function pctCell(v){{
  if(v==null) return '<td class="number"><span class="muted">·</span></td>';
  return `<td class="number ${{v>=0?'pos':'neg'}}">${{fmtPct(v)}}</td>`;
}}

const DEAL_PAGE=50;
let dealPage=1, dealQuery='', dealOpen=null;
function dealToggle(i){{ dealOpen = dealOpen===i ? null : i; renderDeals(); }}
// Detail panel: metrics as rows × quarters as columns (axis flipped vs the main
// table). Ratios are computed from the SUMMED numerators/denominators of the
// filtered rows, never averaged. Bids exist on both branches (Beachfront closing
// + SSP responses, same definition: outgoing bid responses); where a denominator
// is 0 the cell shows · instead of a misleading 0%/∞.
const fmtRate=v=>(v*100).toFixed(2)+'%';
function dealDetailRow(e,colspan){{
  const T='__total__';
  const cols=[...QUARTERS,T];
  const rev=q=>q===T?e.total:e.rev[q], imp=q=>q===T?e.totalI:e.imp[q], bid=q=>q===T?e.totalB:e.bid[q];
  const METRICS=[
    ['💰 Revenue Gross', q=>rev(q)!=null?`<span title="${{fmtUSD2(rev(q))}}">${{fmtUSDc(rev(q))}}</span>`:null],
    ['👁 Impressions',   q=>imp(q)?`<span title="${{fmtInt(imp(q))}}">${{fmtImpc(imp(q))}}</span>`:null],
    ['📤 Outgoing Bids', q=>bid(q)?`<span title="${{fmtInt(bid(q))}}">${{fmtImpc(bid(q))}}</span>`:null],
    ['🎯 Win Rate',      q=>(bid(q)&&imp(q)!=null)?fmtRate(imp(q)/bid(q)):null],
    ['💵 eCPM',          q=>(imp(q)&&rev(q)!=null)?fmtUSD2(rev(q)*1000/imp(q)):null],
  ];
  return `<tr class="detail-row"><td colspan="${{colspan}}"><div class="deal-detail">`+
    `<div class="deal-detail-title">${{escapeHtml(e.ad_name??'—')}} <span class="muted">· ${{escapeHtml(e.advertiser??'—')}}${{(e.deal_id&&e.deal_id!=='nan')?' · '+escapeHtml(e.deal_id):''}}</span></div>`+
    '<table><thead><tr><th></th>'+cols.map(q=>`<th class="number">${{q===T?'Total':fmtQ(q)}}</th>`).join('')+'</tr></thead><tbody>'+
    METRICS.map(([label,cell])=>`<tr><td class="deal-detail-lbl">${{label}}</td>`+
      cols.map(q=>{{const v=cell(q);return `<td class="number${{q===T?' grp-start':''}}">${{v!=null?v:'<span class="muted">·</span>'}}</td>`;}}).join('')+'</tr>').join('')+
    '</tbody></table></div></td></tr>';
}}
function dealFiltered(){{
  if(!dealQuery) return DEALS;
  const q=dealQuery.toLowerCase();
  return DEALS.filter(e=>String(e.clearvu??'').toLowerCase().includes(q)
    ||String(e.ad_name??'').toLowerCase().includes(q)
    ||String(e.deal_id??'').toLowerCase().includes(q)
    ||String(e.advertiser??'').toLowerCase().includes(q));
}}
function renderDeals(){{
  document.getElementById('deal-head').innerHTML =
    '<tr><th class="sticky-col colw-cv">ClearVu Account</th><th class="sticky-col colw-ad">Ad Name</th><th class="sticky-col colw-id">Deal ID</th>'+
    QUARTERS.map(q=>`<th class="number">${{fmtQ(q)}}</th>`).join('')+'<th class="number">Total</th>'+
    `<th class="number grp-start" title="First ${{QTD_DAYS}} completed days of the current quarter">QTD (USD)</th>`+
    `<th class="number" title="QTD vs same ${{QTD_DAYS}} days of the previous quarter">QoQ %</th>`+
    `<th class="number" title="QTD vs same ${{QTD_DAYS}} days of the prior-year quarter">YoY %</th></tr>`;
  const list=dealFiltered();
  const pages=Math.max(1,Math.ceil(list.length/DEAL_PAGE));
  dealPage=Math.min(dealPage,pages);
  const start=(dealPage-1)*DEAL_PAGE, slice=list.slice(start,start+DEAL_PAGE);
  const NCOLS=7+QUARTERS.length;
  document.getElementById('deal-body').innerHTML = slice.map(e=>
    `<tr class="deal-click" onclick="dealToggle(${{e._i}})" title="Click for detail metrics">`+
    `<td class="sticky-col colw-cv" title="${{escapeHtml(e.clearvu)}}"><span class="deal-chev">${{dealOpen===e._i?'▾':'▸'}}</span>${{e.clearvu!=null?escapeHtml(e.clearvu):'<span class="muted">—</span>'}}</td>`+
    `<td class="sticky-col colw-ad" title="${{escapeHtml(e.ad_name)}}">${{e.ad_name!=null?escapeHtml(e.ad_name):'<span class="muted">—</span>'}}</td>`+
    `<td class="sticky-col colw-id" title="${{escapeHtml(e.deal_id)}}">${{(e.deal_id&&e.deal_id!=='nan')?escapeHtml(e.deal_id):'<span class="muted">—</span>'}}</td>`+
    QUARTERS.map(q=>e.rev[q]!=null?`<td class="number" title="${{fmtUSD2(e.rev[q])}}">${{fmtUSDc(e.rev[q])}}</td>`:'<td class="number muted">·</td>').join('')+
    `<td class="number" style="font-weight:600">${{fmtUSD(e.total)}}</td>`+
    (e.qtdCur!=null?`<td class="number grp-start" title="${{fmtUSD2(e.qtdCur)}}">${{fmtUSDc(e.qtdCur)}}</td>`:'<td class="number grp-start muted">·</td>')+
    pctCell(dealGrowth(e,'qtdPrevQ'))+
    pctCell(dealGrowth(e,'qtdPrevY'))+
    '</tr>'+
    `<tr class="imp-row"><td class="sticky-col colw-cv"></td><td class="sticky-col colw-ad">↳ impressions</td><td class="sticky-col colw-id"></td>`+
    QUARTERS.map(q=>e.imp[q]?`<td class="number" title="${{fmtInt(e.imp[q])}}">${{fmtImpc(e.imp[q])}}</td>`:'<td class="number muted">·</td>').join('')+
    `<td class="number" title="${{fmtInt(e.totalI)}}">${{fmtImpc(e.totalI)}}</td>`+
    '<td class="number grp-start muted">·</td><td class="number muted">·</td><td class="number muted">·</td></tr>'+
    (dealOpen===e._i?dealDetailRow(e,NCOLS):'')).join('')
    || '<tr><td class="muted" colspan="'+NCOLS+'">No matching deals</td></tr>';
  const totalRev=list.reduce((s,e)=>s+e.total,0);
  document.getElementById('deal-count').textContent =
    `${{fmtInt(list.length)}} deals · ${{fmtUSD(totalRev)}} · ${{fmtImpc(list.reduce((s,e)=>s+e.totalI,0))}} impressions${{(dealQuery||anyFilter())?' (filtered)':''}}`;
  renderPagination('deal-pag',pages,dealPage,p=>{{dealPage=p;dealOpen=null;renderDeals();}});
}}
function dealSearch(q){{ dealQuery=q.trim(); dealPage=1; dealOpen=null; renderDeals(); }}
function dealCSV(){{
  const list=dealFiltered();
  const header=['ClearVu Account','Ad Name','Deal ID',...QUARTERS.map(fmtQ),'Total','QTD (USD)','QoQ %','YoY %',
    ...QUARTERS.map(q=>fmtQ(q)+' impressions'),'Total impressions',
    ...QUARTERS.map(q=>fmtQ(q)+' bids'),'Total bids',
    ...QUARTERS.map(q=>fmtQ(q)+' win rate'),'Total win rate',
    ...QUARTERS.map(q=>fmtQ(q)+' eCPM'),'Total eCPM'];
  const body=list.map(e=>{{
    const qoq=dealGrowth(e,'qtdPrevQ'), yoy=dealGrowth(e,'qtdPrevY');
    const wr=(i,b)=>b?((i||0)*100/b).toFixed(2)+'%':'';
    const ec=(r,i)=>i?Math.round((r||0)*100000/i)/100:'';
    return [e.clearvu??'',e.ad_name??'',e.deal_id??'',...QUARTERS.map(q=>e.rev[q]??0),e.total,
            e.qtdCur??'', qoq!=null?(qoq*100).toFixed(1)+'%':'', yoy!=null?(yoy*100).toFixed(1)+'%':'',
            ...QUARTERS.map(q=>e.imp[q]??0),e.totalI,
            ...QUARTERS.map(q=>e.bid[q]??0),e.totalB,
            ...QUARTERS.map(q=>wr(e.imp[q],e.bid[q])),wr(e.totalI,e.totalB),
            ...QUARTERS.map(q=>ec(e.rev[q],e.imp[q])),ec(e.total,e.totalI)];
  }});
  downloadCSV([header,...body],'neurox_deals');
}}

// ── Open Auction (ad_name × quarter, Beachfront) — DSP filter only (rows carry no channel/BL) ──
let OA=[];
function buildOA(){{
  const map=new Map();
  filt(OA_ROWS,'oa').forEach(r=>{{
    const key=r.ad_name??'—';
    let e=map.get(key);
    if(!e){{e={{ad_name:r.ad_name,rev:{{}},total:0,qtdCur:null,qtdPrevQ:null,qtdPrevY:null}};map.set(key,e);}}
    const q=qOf(r);
    const v=Number(r.rev_gross)||0;
    e.rev[q]=(e.rev[q]||0)+v; e.total+=v;
    e.qtdCur=addN(e.qtdCur, r.rev_qtd_current!=null?Number(r.rev_qtd_current):null);
    e.qtdPrevQ=addN(e.qtdPrevQ, r.rev_qtd_prev_qtd!=null?Number(r.rev_qtd_prev_qtd):null);
    e.qtdPrevY=addN(e.qtdPrevY, r.rev_qtd_prev_year!=null?Number(r.rev_qtd_prev_year):null);
  }});
  OA=[...map.values()].sort((a,b)=>b.total-a.total);
}}

const OA_PAGE=50;
let oaPage=1, oaQuery='';
function oaFiltered(){{
  if(!oaQuery) return OA;
  const q=oaQuery.toLowerCase();
  return OA.filter(e=>String(e.ad_name??'').toLowerCase().includes(q));
}}
function renderOA(){{
  document.getElementById('oa-head').innerHTML =
    '<tr><th class="sticky-col colw-oa">Ad Name</th>'+
    QUARTERS.map(q=>`<th class="number">${{fmtQ(q)}}</th>`).join('')+'<th class="number">Total</th>'+
    `<th class="number grp-start" title="First ${{QTD_DAYS}} completed days of the current quarter">QTD (USD)</th>`+
    `<th class="number" title="QTD vs same ${{QTD_DAYS}} days of the previous quarter">QoQ %</th>`+
    `<th class="number" title="QTD vs same ${{QTD_DAYS}} days of the prior-year quarter">YoY %</th></tr>`;
  const list=oaFiltered();
  const pages=Math.max(1,Math.ceil(list.length/OA_PAGE));
  oaPage=Math.min(oaPage,pages);
  const start=(oaPage-1)*OA_PAGE, slice=list.slice(start,start+OA_PAGE);
  document.getElementById('oa-body').innerHTML = slice.map(e=>
    `<tr><td class="sticky-col colw-oa" title="${{escapeHtml(e.ad_name)}}">${{e.ad_name!=null?escapeHtml(e.ad_name):'<span class="muted">—</span>'}}</td>`+
    QUARTERS.map(q=>e.rev[q]!=null?`<td class="number" title="${{fmtUSD2(e.rev[q])}}">${{fmtUSDc(e.rev[q])}}</td>`:'<td class="number muted">·</td>').join('')+
    `<td class="number" style="font-weight:600">${{fmtUSD(e.total)}}</td>`+
    (e.qtdCur!=null?`<td class="number grp-start" title="${{fmtUSD2(e.qtdCur)}}">${{fmtUSDc(e.qtdCur)}}</td>`:'<td class="number grp-start muted">·</td>')+
    pctCell(dealGrowth(e,'qtdPrevQ'))+
    pctCell(dealGrowth(e,'qtdPrevY'))+
    '</tr>').join('')
    || '<tr><td class="muted" colspan="'+(5+QUARTERS.length)+'">No matching ad names</td></tr>';
  const totalRev=list.reduce((s,e)=>s+e.total,0);
  document.getElementById('oa-count').textContent =
    `${{fmtInt(list.length)}} ad names · ${{fmtUSD(totalRev)}}${{(oaQuery||anyFilter())?' (filtered)':''}}`;
  renderPagination('oa-pag',pages,oaPage,p=>{{oaPage=p;renderOA();}});
}}
function oaSearch(q){{ oaQuery=q.trim(); oaPage=1; renderOA(); }}
function oaCSV(){{
  const list=oaFiltered();
  const header=['Ad Name',...QUARTERS.map(fmtQ),'Total','QTD (USD)','QoQ %','YoY %'];
  const body=list.map(e=>{{
    const qoq=dealGrowth(e,'qtdPrevQ'), yoy=dealGrowth(e,'qtdPrevY');
    return [e.ad_name??'',...QUARTERS.map(q=>e.rev[q]??0),e.total,
            e.qtdCur??'', qoq!=null?(qoq*100).toFixed(1)+'%':'', yoy!=null?(yoy*100).toFixed(1)+'%':''];
  }});
  downloadCSV([header,...body],'neurox_open_auction');
}}

// ══════════════ Tab 3: Brand Details (adomain × quarter, ONE DSP at a time) ══════════════
// A single-select DSP picker scopes the table to exactly one DSP group. Options
// are the DSPs passing the global filters, sorted by brand revenue; the current
// pick is kept across filter changes when still available, else reset to top.
let BRANDS=[], BRAND_DSP=null;
function buildBrands(){{
  const rows=filt(BRAND_ROWS,'brand');
  // DSP options by revenue under the current global filters
  const dspRev=new Map();
  rows.forEach(r=>{{ const d=r.dsp_group_name??'—'; dspRev.set(d,(dspRev.get(d)||0)+(Number(r.rev_gross)||0)); }});
  const opts=[...dspRev.entries()].sort((a,b)=>b[1]-a[1]).map(e=>e[0]);
  if(!BRAND_DSP||!dspRev.has(BRAND_DSP)) BRAND_DSP=opts[0]||null;
  const sel=document.getElementById('brand-dsp-select');
  sel.innerHTML=opts.map(d=>`<option value="${{escapeHtml(d)}}"${{d===BRAND_DSP?' selected':''}}>${{escapeHtml(d)}} — ${{fmtUSDc(dspRev.get(d))}}</option>`).join('');
  const map=new Map();
  rows.forEach(r=>{{
    if((r.dsp_group_name??'—')!==BRAND_DSP) return;
    const key=r.adomain??'—';
    let e=map.get(key);
    if(!e){{e={{dsp:r.dsp_group_name??'—',brand:r.adomain??'—',rev:{{}},total:0}};map.set(key,e);}}
    const q=qOf(r), v=Number(r.rev_gross)||0;
    e.rev[q]=(e.rev[q]||0)+v; e.total+=v;
  }});
  BRANDS=[...map.values()].sort((a,b)=>b.total-a.total);
}}
function brandDspPick(v){{
  BRAND_DSP=v; brandPage=1;
  buildBrands(); renderBrands();
}}
const BRAND_PAGE=50;
let brandPage=1, brandQuery='';
function brandFiltered(){{
  if(!brandQuery) return BRANDS;
  const q=brandQuery.toLowerCase();
  return BRANDS.filter(e=>String(e.brand??'').toLowerCase().includes(q));
}}
function renderBrands(){{
  document.getElementById('brand-head').innerHTML =
    '<tr><th class="sticky-col colw-br-dsp">DSP Group</th><th class="sticky-col colw-br-brand">Brand (adomain)</th>'+
    BRAND_QUARTERS.map(q=>`<th class="number">${{fmtQ(q)}}</th>`).join('')+
    '<th class="number col-total">Total</th></tr>';
  const list=brandFiltered();
  const pages=Math.max(1,Math.ceil(list.length/BRAND_PAGE));
  brandPage=Math.min(brandPage,pages);
  const start=(brandPage-1)*BRAND_PAGE, slice=list.slice(start,start+BRAND_PAGE);
  document.getElementById('brand-body').innerHTML = slice.map(e=>
    `<tr><td class="sticky-col colw-br-dsp" title="${{escapeHtml(e.dsp)}}">${{escapeHtml(e.dsp)}}</td>`+
    `<td class="sticky-col colw-br-brand" title="${{escapeHtml(e.brand)}}">${{escapeHtml(e.brand)}}</td>`+
    BRAND_QUARTERS.map(q=>e.rev[q]!=null?`<td class="number" title="${{fmtUSD2(e.rev[q])}}">${{fmtUSDc(e.rev[q])}}</td>`:'<td class="number muted">·</td>').join('')+
    `<td class="number col-total" title="${{fmtUSD2(e.total)}}">${{fmtUSD(e.total)}}</td></tr>`).join('')
    || '<tr><td class="muted" colspan="'+(3+BRAND_QUARTERS.length)+'">No matching brands</td></tr>';
  const totalRev=list.reduce((s,e)=>s+e.total,0);
  document.getElementById('brand-count').textContent =
    `${{fmtInt(list.length)}} brands for ${{BRAND_DSP??'—'}} · ${{fmtUSD(totalRev)}}${{(brandQuery||anyFilter())?' (filtered)':''}}`;
  renderPagination('brand-pag',pages,brandPage,p=>{{brandPage=p;renderBrands();}});
}}
function brandSearch(q){{ brandQuery=q.trim(); brandPage=1; renderBrands(); }}
function brandCSV(){{
  const list=brandFiltered();
  const header=['DSP Group','Brand (adomain)',...BRAND_QUARTERS.map(fmtQ),'Total'];
  const body=list.map(e=>[e.dsp??'',e.brand??'',...BRAND_QUARTERS.map(q=>e.rev[q]??0),Math.round(e.total*100)/100]);
  downloadCSV([header,...body],'neurox_brands_'+String(BRAND_DSP??'all').replace(/[^\\w-]+/g,'_'));
}}

// ══════════════ Tab 4: Weekly View (WoW, rolling 7-day windows) ══════════════
// Rows grouped by any combination of Business Line / Connection Type / Product
// Format (chip toggles, at least one always on). Columns: current week, previous
// week, WoW USD, WoW %. Sorted by WoW USD variation desc. Global filters apply.
const WK_DIMS=[
  {{key:'bl', label:'Business Line',   field:'business_line'}},
  {{key:'ct', label:'Connection Type', field:'connection_type'}},
  {{key:'pf', label:'Product Format',  field:'product_category'}},
];
const wkActive=new Set(['bl']);
function wkDimToggle(key){{
  if(wkActive.has(key)){{
    if(wkActive.size===1) return;              // keep at least one dimension
    wkActive.delete(key);
  }} else wkActive.add(key);
  document.querySelectorAll('.wk-dim').forEach(b=>b.classList.toggle('active',wkActive.has(b.dataset.dim)));
  wkPage=1; buildWk(); renderWk();
}}
// Window labels from the build date (rolling weeks, not ISO calendar weeks)
const WK_WINDOWS=(()=>{{
  const day=86400000, end=Date.parse({json.dumps(today)});
  const d=t=>new Date(t).toISOString().slice(0,10);
  return {{cur:`${{d(end-7*day)}} → ${{d(end-day)}}`, prev:`${{d(end-14*day)}} → ${{d(end-8*day)}}`}};
}})();
let WK=[], WK_TOTAL=null;
function buildWk(){{
  const dims=WK_DIMS.filter(x=>wkActive.has(x.key));
  const map=new Map();
  WK_TOTAL={{cur:0,prev:0}};
  filt(WK_ROWS,'wk').forEach(r=>{{
    const key=dims.map(x=>r[x.field]??'—').join('\\u0001');
    let e=map.get(key);
    if(!e){{e={{vals:dims.map(x=>r[x.field]??'—'),cur:0,prev:0}};map.set(key,e);}}
    const v=Number(r.rev_gross)||0;
    if(r.period==='current_week'){{e.cur+=v;WK_TOTAL.cur+=v;}}
    else if(r.period==='previous_week'){{e.prev+=v;WK_TOTAL.prev+=v;}}
  }});
  WK=[...map.values()].sort((a,b)=>(b.cur-b.prev)-(a.cur-a.prev));   // WoW USD desc
}}
const WK_PAGE=50;
let wkPage=1;
function wkPctCell(cur,prev){{
  if(!prev) return '<td class="number"><span class="muted">·</span></td>';
  const p=cur/prev-1;
  return `<td class="number ${{p>=0?'pos':'neg'}}">${{fmtPct(p)}}</td>`;
}}
function wkUsdCell(cur,prev){{
  const d=cur-prev;
  return `<td class="number ${{d>=0?'pos':'neg'}}" title="${{fmtUSD2(d)}}">${{fmtUSDdelta(d)}}</td>`;
}}
function wkRow(vals,cur,prev,cls){{
  return `<tr${{cls?` class="${{cls}}"`:''}}>`+
    vals.map(v=>`<td title="${{escapeHtml(v)}}">${{escapeHtml(v)}}</td>`).join('')+
    `<td class="number" title="${{fmtUSD2(cur)}}">${{fmtUSD(cur)}}</td>`+
    `<td class="number" title="${{fmtUSD2(prev)}}">${{fmtUSD(prev)}}</td>`+
    wkUsdCell(cur,prev)+wkPctCell(cur,prev)+'</tr>';
}}
function renderWk(){{
  const dims=WK_DIMS.filter(x=>wkActive.has(x.key));
  document.getElementById('wk-sub').childNodes[0].textContent =
    `Week-over-week revenue — rolling 7-day windows: current ${{WK_WINDOWS.cur}} vs previous ${{WK_WINDOWS.prev}}. Sorted by WoW USD variation. `;
  document.getElementById('wk-head').innerHTML =
    '<tr>'+dims.map(x=>`<th>${{x.label}}</th>`).join('')+
    `<th class="number" title="${{WK_WINDOWS.cur}}">Current Week</th>`+
    `<th class="number" title="${{WK_WINDOWS.prev}}">Previous Week</th>`+
    '<th class="number">WoW USD</th><th class="number">WoW %</th></tr>';
  const pages=Math.max(1,Math.ceil(WK.length/WK_PAGE));
  wkPage=Math.min(wkPage,pages);
  const start=(wkPage-1)*WK_PAGE, slice=WK.slice(start,start+WK_PAGE);
  let body=slice.map(e=>wkRow(e.vals,e.cur,e.prev)).join('');
  if(WK.length){{
    const tv=['Total',...Array(dims.length-1).fill('')];
    body+=wkRow(tv,WK_TOTAL.cur,WK_TOTAL.prev,'total-row');
  }}
  document.getElementById('wk-body').innerHTML = body || '<tr><td class="muted">No data</td></tr>';
  document.getElementById('wk-count').textContent =
    `${{fmtInt(WK.length)}} rows · current week ${{fmtUSD(WK_TOTAL?WK_TOTAL.cur:0)}} vs previous ${{fmtUSD(WK_TOTAL?WK_TOTAL.prev:0)}}${{anyFilter()?' (filtered)':''}}`;
  renderPagination('wk-pag',pages,wkPage,p=>{{wkPage=p;renderWk();}});
}}
function wkCSV(){{
  const dims=WK_DIMS.filter(x=>wkActive.has(x.key));
  const header=[...dims.map(x=>x.label),`Current Week (${{WK_WINDOWS.cur}})`,`Previous Week (${{WK_WINDOWS.prev}})`,'WoW USD','WoW %'];
  const rowOf=(vals,cur,prev)=>[...vals,Math.round(cur*100)/100,Math.round(prev*100)/100,
    Math.round((cur-prev)*100)/100, prev?((cur/prev-1)*100).toFixed(1)+'%':''];
  const body=WK.map(e=>rowOf(e.vals,e.cur,e.prev));
  if(WK_TOTAL) body.push(rowOf(['Total',...Array(dims.length-1).fill('')],WK_TOTAL.cur,WK_TOTAL.prev));
  downloadCSV([header,...body],'neurox_weekly_wow');
}}

// ══════════════ Crush Q3 · Reactivation (loss tables, worst first) ══════════════
// Loss = 2025 peak month vs Jun 2026 · rows with 2025 peak ≥ $1k · excl. PMP - Seedtag
// (exclusion applied in SQL). Baseline columns Jan 25 – Jun 26; each follow-up month
// is paired with its prior-year (YoY) base column.
const REACT_BLS=['DSP Marketplace - BFM','Select - BFM','Open Auction - BFM'];
const REACT_PILLS={{'DSP Marketplace - BFM':'pill-dspm','Select - BFM':'pill-select','Open Auction - BFM':'pill-oa'}};
let REACT_BL=REACT_BLS[0], reactPage=1, reactQuery='';
const R_MONTHS=[...new Set(REACT_ROWS.map(r=>r.m))].sort();
const R_BASE=R_MONTHS.filter(m=>m<='2026-06');
const R_FU=R_MONTHS.filter(m=>m>='2026-07');
const prevYearM=m=>(parseInt(m.slice(0,4))-1)+m.slice(4);
const fmtM=m=>{{const d=new Date(m+'-01');return d.toLocaleString('en-US',{{month:'short',timeZone:'UTC'}})+' '+String(d.getUTCFullYear()).slice(2);}};
const REACT_MIN_PEAK=1000;
let R_DATA={{}};   // bl → sorted entity list

// Segment pickers (Crush Q3): grouping keys for the loss / new-deal tables.
// At least one segment stays selected; entities are re-aggregated on toggle
// (peak & loss recomputed on the aggregated monthly series — not a sum of peaks).
const CQ3_SEGS=[['dsp','DSP','colw-cv'],['cva','ClearVu Account','colw-ad'],['ad','Ad Name','colw-id']];
let reactSegs={{dsp:true,cva:true,ad:true}}, trkSegs={{dsp:true,cva:true,ad:true}};
function _segToggle(segs,k){{
  if(segs[k]&&Object.values(segs).filter(Boolean).length===1) return false;  // keep ≥1
  segs[k]=!segs[k]; return true;
}}
function _segChips(cls,segs){{
  document.querySelectorAll('.'+cls).forEach(b=>b.classList.toggle('active',!!segs[b.dataset.seg]));
}}
function reactSegToggle(k){{ if(!_segToggle(reactSegs,k)) return; buildReact(); reactPage=1; renderReact(); }}
function trkSegToggle(k){{ if(!_segToggle(trkSegs,k)) return; trkPage=1; renderTrk(); }}

function buildReact(){{
  R_DATA={{}};
  const rows=filt(REACT_ROWS,'react');
  const KS=CQ3_SEGS.filter(([k])=>reactSegs[k]).map(([k])=>k);
  REACT_BLS.forEach(bl=>{{
    const map=new Map();
    rows.forEach(r=>{{
      if(r.bl!==bl) return;
      const key=KS.map(k=>r[k]??'').join('\\u0001');
      let e=map.get(key);
      if(!e){{e={{dsp:reactSegs.dsp?r.dsp:null,cva:reactSegs.cva?r.cva:null,ad:reactSegs.ad?r.ad:null,ids:new Set(),rev:{{}}}};map.set(key,e);}}
      e.rev[r.m]=(e.rev[r.m]||0)+(Number(r.rev)||0);
      String(r.did??'').split(',').map(s=>s.trim()).forEach(i=>{{if(i&&i!=='nan')e.ids.add(i);}});
    }});
    const list=[];
    map.forEach(e=>{{
      let peak=0;
      Object.entries(e.rev).forEach(([m,v])=>{{ if(m<'2026-01'&&v>peak) peak=v; }});
      if(peak<REACT_MIN_PEAK) return;                    // 2025 peak ≥ $1k
      e.peak25=peak;
      e.loss=peak-(e.rev['2026-06']||0);
      e.did=[...e.ids].join(', '); delete e.ids;
      list.push(e);
    }});
    list.sort((a,b)=>b.loss-a.loss);                     // worst first
    R_DATA[bl]=list;
    const pill=document.getElementById(REACT_PILLS[bl]);
    if(pill){{
      const tot=list.reduce((s,e)=>s+e.loss,0);
      pill.innerHTML=`<span class="loss-pill${{tot<0?' gain-pill':''}}">${{tot<0?'+':'−'}}$${{Math.round(Math.abs(tot)/1000).toLocaleString()}}k</span>`;
    }}
  }});
}}
function reactFiltered(){{
  let list=R_DATA[REACT_BL]||[];
  if(!reactQuery) return list;
  const q=reactQuery.toLowerCase();
  return list.filter(e=>String(e.dsp??'').toLowerCase().includes(q)
    ||String(e.cva??'').toLowerCase().includes(q)
    ||String(e.ad??'').toLowerCase().includes(q)
    ||String(e.did??'').toLowerCase().includes(q));
}}
function renderReact(){{
  const isOA=REACT_BL==='Open Auction - BFM';       // no ClearVu column for Open Auction
  document.getElementById('react-title').textContent='Reactivation targets — '+REACT_BL;
  document.querySelectorAll('.react-bl').forEach(b=>b.classList.toggle('active',b.dataset.bl===REACT_BL));
  _segChips('seg-react',reactSegs);
  const segCols=CQ3_SEGS.filter(([k])=>reactSegs[k]&&!(isOA&&k==='cva'));
  const COLW=['colw-cv','colw-ad','colw-id'];
  const labels=segCols.map(([k,t],i)=>[t,COLW[i]]);
  const showDid=!isOA;   // Deal ID column for DSP Marketplace & Select only
  document.getElementById('react-head').innerHTML='<tr>'+
    labels.map(([t,c],i)=>`<th class="sticky-col ${{c}}">${{t}}</th>`).join('')+
    (showDid?'<th>Deal IDs</th>':'')+
    R_BASE.map((m,i)=>`<th class="number${{i===0?' grp-start':''}}">${{fmtM(m)}}</th>`).join('')+
    R_FU.map(m=>`<th class="number grp-start" title="follow-up month">${{fmtM(m)}} →</th><th class="number muted" title="prior-year base for YoY">${{fmtM(prevYearM(m))}} (YoY)</th>`).join('')+
    '<th class="number grp-start" title="2025 peak month">Peak 25</th><th class="number" title="2025 peak vs Jun 2026">Loss</th></tr>';
  const list=reactFiltered();
  const pages=Math.max(1,Math.ceil(list.length/25));
  reactPage=Math.min(reactPage,pages);
  const start=(reactPage-1)*25, slice=list.slice(start,start+25);
  const cell=v=>v!=null&&v!==0?`<td class="number" title="${{fmtUSD2(v)}}">${{fmtUSDc(v)}}</td>`:'<td class="number muted">·</td>';
  document.getElementById('react-body').innerHTML=slice.map(e=>{{
    const lab=segCols.map(([k],i)=>`<td class="sticky-col ${{COLW[i]}}" title="${{escapeHtml(e[k])}}">${{escapeHtml(e[k]??'—')}}</td>`).join('');
    const didTd=showDid?`<td class="muted" title="${{escapeHtml(e.did)}}">${{escapeHtml(String(e.did??'').slice(0,18))}}${{String(e.did??'').length>18?'…':''}}</td>`:'';
    return '<tr>'+lab+didTd+
      R_BASE.map((m,i)=>i===0?cell(e.rev[m]).replace('<td class="number','<td class="number grp-start'):cell(e.rev[m])).join('')+
      R_FU.map(m=>cell(e.rev[m]).replace('<td class="number','<td class="number grp-start')+cell(e.rev[prevYearM(m)])).join('')+
      `<td class="number grp-start" title="${{fmtUSD2(e.peak25)}}">${{fmtUSDc(e.peak25)}}</td>`+
      `<td class="number neg" title="${{fmtUSD2(e.loss)}}">−${{fmtUSDc(Math.abs(e.loss))}}</td></tr>`;
  }}).join('') || '<tr><td class="muted">No rows (2025 peak ≥ $1k) match</td></tr>';
  const totLoss=list.reduce((s,e)=>s+e.loss,0);
  document.getElementById('react-count').textContent=
    `${{fmtInt(list.length)}} reactivation targets · total loss ${{fmtUSD(totLoss)}}${{reactQuery?' (searched)':''}}`;
  renderPagination('react-pag',pages,reactPage,p=>{{reactPage=p;renderReact();}});
}}
function showReactBL(bl){{ REACT_BL=bl; reactPage=1; renderReact(); }}
function reactSearch(q){{ reactQuery=q.trim(); reactPage=1; renderReact(); }}
function reactCSV(){{
  const list=reactFiltered();
  const segCols=CQ3_SEGS.filter(([k])=>reactSegs[k]);
  const header=[...segCols.map(([,t])=>t),'Deal IDs',...R_BASE,...R_FU.flatMap(m=>[m,prevYearM(m)+' (YoY)']),'2025 peak','Loss (peak vs Jun26)'];
  const body=list.map(e=>[...segCols.map(([k])=>e[k]??''),e.did??'',
    ...R_BASE.map(m=>e.rev[m]??0),
    ...R_FU.flatMap(m=>[e.rev[m]??0,e.rev[prevYearM(m)]??0]),
    Math.round(e.peak25*100)/100, Math.round(e.loss*100)/100]);
  downloadCSV([header,...body],'crushq3_reactivation_'+REACT_BL.replace(/[^\\w-]+/g,'_'));
}}

// ══════════════ Crush Q3 · New Deals (tracker) ══════════════
let trkPage=1, trkQuery='', TRK_MONTH='all';
const TRK_BY_AD=(()=>{{ const m=new Map(); TRK_SERIES.forEach(r=>{{ (m.get(r.ad)||m.set(r.ad,new Map()).get(r.ad)).set(r.d,Number(r.rev)||0); }}); return m; }})();
const TRK_END=TRK_SERIES.length?TRK_SERIES.map(r=>r.d).sort().at(-1):null;
function sparkSVG(ads,activation){{
  // ads: one deal name or a list (grouped rows) — series are summed per day
  const sers=(Array.isArray(ads)?ads:[ads]).map(a=>TRK_BY_AD.get(a)).filter(Boolean);
  if(!sers.length||!TRK_END) return '';
  const days=[]; let d=new Date(activation);
  const end=new Date(TRK_END);
  while(d<=end){{ days.push(d.toISOString().slice(0,10)); d=new Date(d.getTime()+86400000); }}
  const vals=days.map(x=>sers.reduce((s,m)=>s+(m.get(x)||0),0));
  const mx=Math.max(...vals,1);
  const W=110,H=26;
  const pts=vals.map((v,i)=>`${{(i/(Math.max(vals.length-1,1))*W).toFixed(1)}},${{(H-2-(v/mx)*(H-4)).toFixed(1)}}`).join(' ');
  return `<svg class="sparkline" width="${{W}}" height="${{H}}" viewBox="0 0 ${{W}} ${{H}}"><polyline points="${{pts}}" fill="none" stroke="var(--accent)" stroke-width="1.5"/></svg>`;
}}
function trkDeals(){{   // per-deal rows after global filters / month / search (pre-grouping)
  let list=filt(TRK_DEALS,'trk');
  if(TRK_MONTH!=='all') list=list.filter(r=>String(r.activation_date).slice(0,7)===TRK_MONTH);
  if(trkQuery){{
    const q=trkQuery.toLowerCase();
    list=list.filter(r=>String(r.deal_name??'').toLowerCase().includes(q)
      ||String(r.dsp_group_name??'').toLowerCase().includes(q)
      ||String(r.clearvu_account??'').toLowerCase().includes(q)
      ||String(r.deal_ids??'').toLowerCase().includes(q));
  }}
  return list;
}}
function trkFiltered(){{
  const list=trkDeals();
  // group by the selected segments (all three on = one row per deal, as before)
  const FLD={{dsp:'dsp_group_name',cva:'clearvu_account',ad:'deal_name'}};
  const KS=CQ3_SEGS.filter(([k])=>trkSegs[k]).map(([k])=>k);
  const map=new Map();
  list.forEach(r=>{{
    const key=KS.map(k=>r[FLD[k]]??'').join('\\u0001');
    let e=map.get(key);
    if(!e){{
      e={{dsp_group_name:trkSegs.dsp?r.dsp_group_name:null,
          clearvu_account:trkSegs.cva?r.clearvu_account:null,
          deal_name:trkSegs.ad?r.deal_name:null,
          ads:[],bls:new Set(),ids:new Set(),revenue_since_activation:0,
          activation_date:r.activation_date,last_seen:r.last_seen,n:0}};
      map.set(key,e);
    }}
    e.ads.push(r.deal_name); e.bls.add(r.business_line??'—');
    String(r.deal_ids??'').split(',').map(s=>s.trim()).forEach(i=>{{if(i&&i!=='nan')e.ids.add(i);}});
    e.revenue_since_activation+=Number(r.revenue_since_activation)||0;
    if(r.activation_date<e.activation_date)e.activation_date=r.activation_date;
    if(r.last_seen>e.last_seen)e.last_seen=r.last_seen;
    e.n++;
  }});
  return [...map.values()].map(e=>{{
    // active days = distinct dates with revenue across the group's daily series
    const days=new Set();
    e.ads.forEach(a=>{{const s=TRK_BY_AD.get(a); if(s)s.forEach((v,d)=>{{if(v)days.add(d);}});}});
    return {{...e,business_line:[...e.bls].join(', '),deal_ids:[...e.ids].join(', '),
             active_days:days.size}};
  }}).sort((a,b)=>b.revenue_since_activation-a.revenue_since_activation);
}}
function buildTrk(){{
  const months=[...new Set(TRK_DEALS.map(r=>String(r.activation_date).slice(0,7)))].sort();
  const sel=document.getElementById('trk-month-select');
  const cur=TRK_MONTH;
  sel.innerHTML='<option value="all">All (global)</option>'+months.map(m=>`<option value="${{m}}"${{m===cur?' selected':''}}>${{fmtM(m)}}</option>`).join('');
  document.getElementById('trk-data-end').textContent=TRK_END?` · data through ${{TRK_END}}`:'';
}}
function renderTrk(){{
  _segChips('seg-trk',trkSegs);
  // KPI cards — per-deal stats (independent of segment grouping, honour filters)
  const deals=trkDeals();
  const earning=deals.filter(r=>(Number(r.revenue_since_activation)||0)>=0.01);
  const idle=deals.length-earning.length;
  const earned=earning.reduce((s,r)=>s+(Number(r.revenue_since_activation)||0),0);
  document.getElementById('trk-kpis').innerHTML=`
    <div class="kpi-card"><div class="kpi-label">🚀 Fresh Off the Press</div>
      <div class="kpi-value">${{fmtInt(deals.length)}}</div>
      <div class="kpi-sub">new deals activated since Jul 1</div></div>
    <div class="kpi-card"><div class="kpi-label">💸 Already Printing</div>
      <div class="kpi-value">${{fmtInt(earning.length)}}</div>
      <div class="kpi-sub">delivering revenue · ${{fmtUSD(earned)}} so far</div></div>
    <div class="kpi-card"><div class="kpi-label">🛫 On the Launchpad</div>
      <div class="kpi-value">${{fmtInt(idle)}}</div>
      <div class="kpi-sub">signed but no revenue yet</div></div>`;
  const grouped=!trkSegs.ad;   // without Ad Name rows aggregate several deals
  document.getElementById('trk-head').innerHTML=
    '<tr><th class="sticky-col colw-cv">Activation'+(grouped?' (first)':'')+'</th>'+
    (trkSegs.ad?'<th class="sticky-col colw-ad">Deal (ad name)</th>':'')+
    (trkSegs.dsp?'<th>DSP</th>':'')+
    (trkSegs.cva?'<th>ClearVu Account</th>':'')+
    '<th>Business Line</th>'+(grouped?'<th class="number"># Deals</th>':'')+
    '<th class="number">Revenue since activation</th><th class="number">Active days</th><th>Last seen</th><th>Trend (daily)</th><th>Deal IDs</th></tr>';
  const list=trkFiltered();
  const pages=Math.max(1,Math.ceil(list.length/25));
  trkPage=Math.min(trkPage,pages);
  const start=(trkPage-1)*25, slice=list.slice(start,start+25);
  const segTd=(v,sticky)=>`<td${{sticky?' class="sticky-col colw-ad"':''}} title="${{escapeHtml(v)}}">${{v!=null&&v!==''?escapeHtml(v):'<span class="muted">—</span>'}}</td>`;
  document.getElementById('trk-body').innerHTML=slice.map(r=>`<tr>
    <td class="sticky-col colw-cv">${{r.activation_date}}</td>
    ${{trkSegs.ad?segTd(r.deal_name,true):''}}
    ${{trkSegs.dsp?segTd(r.dsp_group_name):''}}
    ${{trkSegs.cva?segTd(r.clearvu_account):''}}
    <td>${{escapeHtml(r.business_line??'—')}}</td>
    ${{grouped?`<td class="number">${{fmtInt(r.n)}}</td>`:''}}
    <td class="number" title="${{fmtUSD2(r.revenue_since_activation)}}">${{fmtUSD(r.revenue_since_activation)}}</td>
    <td class="number">${{fmtInt(r.active_days)}}</td>
    <td>${{r.last_seen}}</td>
    <td>${{sparkSVG(r.ads,r.activation_date)}}</td>
    <td class="muted" title="${{escapeHtml(r.deal_ids)}}">${{escapeHtml(String(r.deal_ids??'').slice(0,24))}}${{String(r.deal_ids??'').length>24?'…':''}}</td>
  </tr>`).join('') || '<tr><td class="muted">No new deals match</td></tr>';
  const tot=list.reduce((s,r)=>s+(Number(r.revenue_since_activation)||0),0);
  document.getElementById('trk-count').textContent=
    `${{fmtInt(list.length)}} new deals · ${{fmtUSD(tot)}} since activation${{TRK_MONTH!=='all'?' · '+fmtM(TRK_MONTH):''}}`;
  renderPagination('trk-pag',pages,trkPage,p=>{{trkPage=p;renderTrk();}});
}}
function trkMonthPick(v){{ TRK_MONTH=v; trkPage=1; renderTrk(); }}
function trkSearch(q){{ trkQuery=q.trim(); trkPage=1; renderTrk(); }}
function trkCSV(){{
  const list=trkFiltered();
  const header=['Activation','Deal (ad name)','DSP','ClearVu Account','Business Line','Revenue since activation','Active days','Last seen','Deal IDs'];
  const body=list.map(r=>[r.activation_date,r.deal_name??'',r.dsp_group_name??'',r.clearvu_account??'',r.business_line??'',r.revenue_since_activation,r.active_days,r.last_seen,r.deal_ids??'']);
  downloadCSV([header,...body],'crushq3_new_deals');
}}

// ══════════════ boot / rebuild ══════════════
function rebuildAll(){{
  buildCom(); OVERVIEWS.forEach(ovBuild); buildDeals(); buildOA(); buildBrands(); buildWk(); buildReact(); buildTrk();
  renderCom(); OVERVIEWS.forEach(ovRender); renderDeals(); renderOA(); renderBrands(); renderWk(); renderReact(); renderTrk();
}}
document.addEventListener('DOMContentLoaded',()=>{{
  buildFilters();
  rebuildAll();
}});
</script>
</body>
</html>"""
