"""Three-tab deals dashboard generator — fully self-contained (no server).

Tab 1  DSP Overview  — advertiser × quarter: deals, revenue, avg spend, QoQ/YoY
Tab 2  Deal Overview — (clearvu_account, ad_name, deal_id) × quarter: revenue
Tab 3  Open Auction  — ad_name × quarter (Beachfront 'Open Auction - BFM' only)

All tabs sort rows by total rev_gross descending. All pivots are computed
client-side from two embedded datasets: deals rows (Tabs 1–2, from
consolidated_deals.sql) and open-auction rows (Tab 3, from open_auction.sql —
a separate query because one combined statement exceeded cluster memory).
"""

from __future__ import annotations

import json


def _logo_tag(b64: str, size: int) -> str:
    return f'<img src="data:image/png;base64,{b64}" alt="Seedtag" style="width:{size}px;height:{size}px">'


def generate_html(
    *,
    rows: list[dict],
    oa_rows: list[dict],
    quarters: list[str],
    sql_text: str,
    logo_b64: str,
    date_from: str,
    today: str,
    now: str,
) -> str:
    rows_json = json.dumps(rows, default=str, ensure_ascii=False)
    oa_json = json.dumps(oa_rows, default=str, ensure_ascii=False)
    quarters_json = json.dumps(quarters)
    logo32 = _logo_tag(logo_b64, 32)
    logo20 = _logo_tag(logo_b64, 20)

    return f"""<!DOCTYPE html>
<html lang="en" data-theme="auto">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Ad Exchange Deals Dashboard — {today}</title>
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
.header-meta{{position:absolute;top:18px;right:64px;text-align:right;font-size:11px;color:var(--text-muted);background:var(--surface-2);padding:6px 12px;border-radius:6px;border:1px solid var(--border)}}
.header-meta .lbl{{font-size:10px;color:var(--text-subtle)}}
.header-meta .val{{font-weight:600;color:var(--text);white-space:nowrap}}

#theme-toggle{{position:fixed;top:16px;right:16px;width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;background:var(--surface);color:var(--text);border:1px solid var(--border);border-radius:50%;cursor:pointer;z-index:10000;box-shadow:0 2px 8px rgba(0,0,0,.08);transition:transform 150ms}}
#theme-toggle:hover{{transform:scale(1.05)}}
#theme-toggle .icon-moon{{display:none}}
html[data-theme="dark"] #theme-toggle .icon-sun{{display:none}}
html[data-theme="dark"] #theme-toggle .icon-moon{{display:inline}}
@media(prefers-color-scheme:dark){{html[data-theme="auto"] #theme-toggle .icon-sun{{display:none}}html[data-theme="auto"] #theme-toggle .icon-moon{{display:inline}}}}

/* DSP filter (global, applies to all tabs) */
.filter-slot{{margin-left:auto;display:flex;align-items:center;gap:8px;padding-bottom:8px}}
.flabel{{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.05em;color:var(--text-subtle)}}
.ms-wrap{{position:relative}}
.ms-trigger{{display:flex;align-items:center;justify-content:space-between;gap:6px;padding:7px 10px;background:var(--surface);border:1px solid var(--border);border-radius:6px;cursor:pointer;height:32px;font-size:13px;color:var(--text);min-width:180px}}
.ms-trigger:hover,.ms-trigger.open{{border-color:var(--accent)}}
.ms-trigger .ms-label{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:190px}}
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
.ms-option .ms-rev{{margin-left:auto;color:var(--text-subtle);font-size:11px;flex-shrink:0}}
.ms-footer{{padding:8px;border-top:1px solid var(--border);display:flex;justify-content:flex-end}}
.ms-footer button{{padding:5px 14px;background:transparent;color:var(--text-muted);border:1px solid var(--border);border-radius:5px;font-size:12px;cursor:pointer}}
.ms-footer button:hover{{border-color:var(--accent);color:var(--accent)}}

/* Tabs */
.tabs-bar{{display:flex;gap:4px;padding:14px 32px 0;background:var(--surface);border-bottom:1px solid var(--border)}}
.tab-btn{{border:1px solid var(--border);border-bottom:none;background:var(--surface-2);color:var(--text-muted);font-family:'Instrument Sans',sans-serif;font-size:14px;font-weight:600;padding:10px 22px;border-radius:10px 10px 0 0;cursor:pointer;position:relative;top:1px}}
.tab-btn:hover{{color:var(--text)}}
.tab-btn.active{{background:var(--bg);color:var(--text);border-color:var(--border)}}
.tab-panel{{display:none;padding:28px 32px}}
.tab-panel.active{{display:block}}

.section-title{{font-size:16px;font-weight:600;margin:26px 0 12px;display:flex;align-items:center;gap:8px}}
.section-title:first-child{{margin-top:0}}
.section-sub{{color:var(--text-subtle);font-size:13px;margin-bottom:14px}}

.card{{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:22px}}
.card-header{{display:flex;align-items:center;gap:8px;margin-bottom:14px;font-weight:600;font-size:14px}}
.card-header .spacer{{flex:1}}
.info-icon{{width:20px;height:20px;background:#238636;color:#fff;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;cursor:pointer;flex-shrink:0;font-style:italic}}
.info-icon:hover{{opacity:.85}}
.btn-csv{{padding:6px 14px;background:var(--accent);color:var(--accent-ink);border:none;border-radius:6px;font-size:12px;cursor:pointer;font-weight:600}}
.btn-csv:hover{{opacity:.9}}

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
/* grouped header (Tab 1 sections) */
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
  .header-meta{{display:none}} .search-box{{min-width:100%}}
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
    <h1>Ad Exchange Deals Dashboard</h1>
    <div class="subtitle">Analytics Team &middot; Revenue Gross (USD) &middot; deals since {date_from} &middot; quarterly</div>
  </div>
  <div class="header-meta">
    <div class="lbl">Last updated</div>
    <div class="val">{now}</div>
  </div>
</header>

<div class="tabs-bar">
  <button class="tab-btn active" data-tab="dsp" onclick="showTab('dsp')">📊 DSP Overview</button>
  <button class="tab-btn" data-tab="deal" onclick="showTab('deal')">🎯 Deal Overview</button>
  <button class="tab-btn" data-tab="oa" onclick="showTab('oa')">🏷️ Open Auction</button>
  <div class="filter-slot">
    <span class="flabel">DSP filter</span>
    <div class="ms-wrap">
      <div class="ms-trigger" id="dsp-filter-trigger" onclick="msToggle()">
        <span class="ms-label" id="dsp-filter-label">All DSPs</span><span class="ms-arrow">▼</span>
      </div>
      <div class="ms-dropdown" id="dsp-filter-dd">
        <div class="ms-search"><input type="text" id="dsp-filter-search" placeholder="Search DSP…" oninput="msSearch(this.value)"></div>
        <div class="ms-options" id="dsp-filter-options"></div>
        <div class="ms-footer"><button onclick="dspFilterClear()">Clear</button></div>
      </div>
    </div>
  </div>
</div>

<!-- ── Tab 1: DSP Overview ── -->
<div class="tab-panel active" id="panel-dsp">
  <div class="section-sub">DSP (advertiser) performance by quarter — deal-based demand only (Open Auction excluded). Sorted by total revenue.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-1')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-1"></div>
  </div>

  <div class="card">
    <div class="card-header">📊 DSP Performance by Quarter
      <span class="muted" style="font-weight:400">— three sections: 🧾 Number of Deals · 💰 Revenue · ⚖️ Avg Spend per Deal</span>
      <div class="spacer"></div><button class="btn-csv" onclick="dspCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="dsp-head"></thead><tbody id="dsp-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="dsp-count"></span><div class="pagination" id="dsp-pag"></div></div>
  </div>
</div>

<!-- ── Tab 2: Deal Overview ── -->
<div class="tab-panel" id="panel-deal">
  <div class="section-sub">Revenue gross per deal by quarter. Sorted by total revenue.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-2')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-2"></div>
  </div>
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

<!-- ── Tab 3: Open Auction ── -->
<div class="tab-panel" id="panel-oa">
  <div class="section-sub">Open Auction revenue gross by ad name per quarter (Beachfront). Sorted by total revenue.
    <span class="info-icon" title="View SQL" onclick="toggleTooltip(event,'sql-tip-3')" style="vertical-align:-5px;margin-left:4px">i</span>
    <div class="tooltip" id="sql-tip-3"></div>
  </div>
  <div class="card">
    <div class="card-header">🏷️ Open Auction <span class="badge-internal">Internal</span>
      <div class="spacer"></div>
      <input class="search-box" id="oa-search" placeholder="Search ad name…" oninput="oaSearch(this.value)">
      <button class="btn-csv" onclick="oaCSV()">📥 CSV</button>
    </div>
    <div class="table-wrapper"><table><thead id="oa-head"></thead><tbody id="oa-body"></tbody></table></div>
    <div class="table-meta"><span class="count" id="oa-count"></span><div class="pagination" id="oa-pag"></div></div>
  </div>
</div>

<footer class="report-footer">
  {logo20}
  Analytics Team &middot; Ad Exchange Deals Dashboard &middot; {today}
</footer>

<script>
const ROWS = {rows_json};
const OA_DATA = {oa_json};
const QUARTERS = {quarters_json};   // sorted ISO quarter-start dates
const SQL_TEXT = {json.dumps(sql_text)};

// ── helpers ──
const fmtUSD  = n => '$' + (Number(n)||0).toLocaleString('en-US',{{maximumFractionDigits:0}});
const fmtUSD2 = n => '$' + (Number(n)||0).toLocaleString('en-US',{{minimumFractionDigits:2,maximumFractionDigits:2}});
const fmtUSDc = n => '$' + Intl.NumberFormat('en-US',{{notation:'compact',maximumFractionDigits:1}}).format(Number(n)||0);
const fmtInt  = n => (Number(n)||0).toLocaleString('en-US');
function fmtQ(iso){{ const d=new Date(String(iso).slice(0,10)); return d.getUTCFullYear()+' Q'+(Math.floor(d.getUTCMonth()/3)+1); }}
function escapeHtml(s){{return String(s??'').replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));}}

// theme
document.getElementById('theme-toggle').addEventListener('click',()=>{{
  const h=document.documentElement, cur=h.getAttribute('data-theme')||'auto';
  const next=cur==='auto'?'light':cur==='light'?'dark':'auto';
  h.setAttribute('data-theme',next); localStorage.setItem('seedtag-theme',next);
}});

// SQL tooltips
['sql-tip-1','sql-tip-2','sql-tip-3'].forEach(id=>{{
  const t=document.getElementById(id);
  t.innerHTML=escapeHtml(SQL_TEXT)+'<span class="copy-hint">Click to copy</span>';
  t.addEventListener('click',()=>{{
    navigator.clipboard&&navigator.clipboard.writeText(SQL_TEXT);
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

// tabs
function showTab(name){{
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.toggle('active',b.dataset.tab===name));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('active',p.id==='panel-'+name));
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

// ══════════════ Tab 1: DSP aggregates ══════════════
// A quarter is "complete" once the next quarter has started (relative to build date).
const BUILD_TS = Date.parse({json.dumps(today)});
function qComplete(q){{
  const d=new Date(String(q).slice(0,10));
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth()+3, 1) <= BUILD_TS;
}}
const fmtPct = v => (v>=0?'+':'−') + Math.abs(v*100).toFixed(1) + '%';
const fmtUSDdelta = v => (v>=0?'+':'−') + fmtUSDc(Math.abs(v));

// Two embedded datasets: ROWS (deals — DSP/Deal Overview tabs) and OA_DATA
// (Beachfront Open Auction, ad_name grain — Open Auction tab). They come from
// separate queries (one combined statement exceeded cluster memory).
const DEAL_ROWS = ROWS;
const OA_ROWS   = OA_DATA;

// Days of the current quarter that are complete (window size used by the SQL build).
const QTD_DAYS = (()=>{{
  const d=new Date(BUILD_TS);
  const qs=Date.UTC(d.getUTCFullYear(), 3*Math.floor(d.getUTCMonth()/3), 1);
  return Math.round((BUILD_TS-qs)/86400000);
}})();

// Comparison column definitions (same for every DSP/deal).
// QoQ: each quarter vs the previous one; YoY: each quarter vs the same quarter a
// year earlier (when present). Complete quarters compare full data; the current
// partial quarter compares day-matched QTD windows computed in SQL.
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
// Variation values for one entity (DSP or deal) against one comparison.
// Entities carry rev{{}} (full-quarter sums) + qtdCur/qtdPrevQ/qtdPrevY (day-matched).
function cmpVals(e,c){{
  let cur, prev;
  if(c.partial){{ cur=e.qtdCur; prev=(c.kind==='qoq')?e.qtdPrevQ:e.qtdPrevY; }}
  else {{ cur=e.rev[c.q]; prev=e.rev[c.prev]; }}
  if(prev==null||prev===0||cur==null) return null;
  return {{pct:cur/prev-1, usd:cur-prev}};
}}
const addN=(a,b)=> b==null ? a : (a==null ? b : a+b);   // null-preserving sum

// per advertiser × quarter: revenue + distinct deal (ad_name) set + QTD windows
const DSP = (()=>{{
  const map=new Map();
  DEAL_ROWS.forEach(r=>{{
    const a=r.advertiser??'—';
    let e=map.get(a); if(!e){{e={{advertiser:a,rev:{{}},deals:{{}},revTotal:0,dealSetAll:new Set(),qtdCur:null,qtdPrevQ:null,qtdPrevY:null}};map.set(a,e);}}
    const q=String(r.quarter).slice(0,10);
    const v=Number(r.rev_gross)||0;
    e.rev[q]=(e.rev[q]||0)+v; e.revTotal+=v;
    e.qtdCur=addN(e.qtdCur, r.rev_qtd_current!=null?Number(r.rev_qtd_current):null);
    e.qtdPrevQ=addN(e.qtdPrevQ, r.rev_qtd_prev_qtd!=null?Number(r.rev_qtd_prev_qtd):null);
    e.qtdPrevY=addN(e.qtdPrevY, r.rev_qtd_prev_year!=null?Number(r.rev_qtd_prev_year):null);
    if(r.ad_name!=null){{ (e.deals[q]=e.deals[q]||new Set()).add(r.ad_name); e.dealSetAll.add(r.ad_name); }}
  }});
  const list=[...map.values()].sort((a,b)=>b.revTotal-a.revTotal);  // rev_gross DESC
  list.forEach(e=>{{
    e.nDeals={{}}; QUARTERS.forEach(q=>{{ e.nDeals[q]=e.deals[q]?e.deals[q].size:0; }});
    e.nDealsTotal=e.dealSetAll.size;
    e.avg={{}}; QUARTERS.forEach(q=>{{ e.avg[q]=e.nDeals[q]?(e.rev[q]||0)/e.nDeals[q]:null; }});
    e.avgTotal=e.nDealsTotal?e.revTotal/e.nDealsTotal:null;
    delete e.deals; delete e.dealSetAll;
  }});
  return list;
}})();

const DSP_PAGE=25;
let dspPage=1;
// Plain sections: one column per quarter. Variation sections (`cmps`): one %/USD
// column PAIR per comparison, collapsible (collapsed by default). The current
// partial quarter's comparisons are day-matched (· QTD, first QTD_DAYS days).
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
const sectionCollapsed={{qoq:true, yoy:true}};
function toggleSection(key){{ sectionCollapsed[key]=!sectionCollapsed[key]; renderDsp(); }}
function cmpTitle(c){{ return c.partial?`Day-matched: first ${{QTD_DAYS}} completed days of each quarter`:''; }}

function renderDsp(){{
  const nQ=QUARTERS.length;
  const width=s=>{{
    if(s.collapsible&&sectionCollapsed[s.key]) return 1;
    return s.cmps ? s.cmps.length*2 : nQ;
  }};
  // Row 1 — section groups (DSP column spans all 3 header rows)
  let h='<tr><th rowspan="3" class="sticky-col colw-dsp" style="vertical-align:bottom">DSP (Advertiser)</th>'+
    SECTIONS.map(s=>{{
      const coll=s.collapsible&&sectionCollapsed[s.key];
      const cls='grp'+(s.collapsible?' grp-click':'');
      const attrs=s.collapsible?` onclick="toggleSection('${{s.key}}')" title="Click to ${{coll?'expand':'collapse'}}"`:'';
      const arrow=s.collapsible?(coll?' ▸':' ▾'):'';
      return `<th class="${{cls}}" colspan="${{width(s)}}"${{attrs}}>${{s.label}}${{arrow}}</th>`;
    }}).join('')+'</tr>';
  // Row 2 — quarter labels (span rows 2–3) or comparison labels (span 2 cols)
  h+='<tr>'+SECTIONS.map(s=>{{
    if(s.collapsible&&sectionCollapsed[s.key]) return '<th class="grp-start" rowspan="2"></th>';
    if(s.cmps) return s.cmps.map((c,i)=>`<th class="number${{i===0?' grp-start':' pair-start'}}" colspan="2" title="${{cmpTitle(c)}}">${{c.label}}</th>`).join('');
    return QUARTERS.map((q,i)=>`<th class="number${{i===0?' grp-start':''}}" rowspan="2">${{fmtQ(q)}}</th>`).join('');
  }}).join('')+'</tr>';
  // Row 3 — % / USD sub-headers under each comparison
  h+='<tr>'+SECTIONS.map(s=>{{
    if(!s.cmps||sectionCollapsed[s.key]) return '';
    return s.cmps.map((c,i)=>`<th class="number${{i===0?' grp-start':' pair-start'}}">%</th><th class="number">USD</th>`).join('');
  }}).join('')+'</tr>';
  document.getElementById('dsp-head').innerHTML=h;

  const LIST=DSP.filter(e=>dspMatch(e.advertiser));
  const pages=Math.max(1,Math.ceil(LIST.length/DSP_PAGE));
  dspPage=Math.min(dspPage,pages);
  const start=(dspPage-1)*DSP_PAGE, slice=LIST.slice(start,start+DSP_PAGE);
  document.getElementById('dsp-body').innerHTML = slice.map(e=>
    `<tr><td class="sticky-col colw-dsp" title="${{escapeHtml(e.advertiser)}}">${{escapeHtml(e.advertiser)}}</td>`+
    SECTIONS.map(s=>{{
      if(s.collapsible&&sectionCollapsed[s.key]) return '<td class="collapsed-cell grp-start">⋯</td>';
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
    || '<tr><td class="muted">No data</td></tr>';
  document.getElementById('dsp-count').textContent =
    `${{fmtInt(LIST.length)}} DSPs · sorted by total revenue${{selectedDSP.size?' (filtered)':''}}`;
  renderPagination('dsp-pag',pages,dspPage,p=>{{dspPage=p;renderDsp();}});
}}
function dspCSV(){{
  // CSV always exports every section fully expanded; variations as two columns each.
  const header=['DSP (Advertiser)'];
  SECTIONS.forEach(s=>{{
    const name=s.label.replace(/^[^ ]+ /,'');
    if(s.cmps) s.cmps.forEach(c=>{{ header.push(`${{name}} ${{c.label}} %`, `${{name}} ${{c.label}} USD`); }});
    else QUARTERS.forEach(q=>header.push(`${{name}} ${{fmtQ(q)}}`));
  }});
  const body=DSP.filter(e=>dspMatch(e.advertiser)).map(e=>{{
    const row=[e.advertiser];
    SECTIONS.forEach(s=>{{
      if(s.cmps) s.cmps.forEach(c=>{{
        const v=cmpVals(e,c);
        row.push(v?(v.pct*100).toFixed(1)+'%':'', v?Math.round(v.usd*100)/100:'');
      }});
      else QUARTERS.forEach(q=>row.push(s.csv(e,q)));
    }});
    return row;
  }});
  downloadCSV([header,...body],'adex_dsp_overview');
}}

// ══════════════ Tab 2: Deal pivot ══════════════
const DEALS = (()=>{{
  const map=new Map();
  DEAL_ROWS.forEach(r=>{{
    const key=[r.clearvu_account??'',r.ad_name??'',r.deal_id??''].join('\\u0001');
    let e=map.get(key);
    if(!e){{e={{clearvu:r.clearvu_account,ad_name:r.ad_name,deal_id:r.deal_id,advertiser:r.advertiser,advSet:new Set(),rev:{{}},total:0,qtdCur:null,qtdPrevQ:null,qtdPrevY:null}};map.set(key,e);}}
    const q=String(r.quarter).slice(0,10);
    const v=Number(r.rev_gross)||0;
    if(r.advertiser!=null) e.advSet.add(r.advertiser);
    e.rev[q]=(e.rev[q]||0)+v; e.total+=v;
    e.qtdCur=addN(e.qtdCur, r.rev_qtd_current!=null?Number(r.rev_qtd_current):null);
    e.qtdPrevQ=addN(e.qtdPrevQ, r.rev_qtd_prev_qtd!=null?Number(r.rev_qtd_prev_qtd):null);
    e.qtdPrevY=addN(e.qtdPrevY, r.rev_qtd_prev_year!=null?Number(r.rev_qtd_prev_year):null);
  }});
  return [...map.values()].sort((a,b)=>b.total-a.total);   // rev_gross DESC
}})();
// Day-matched growth for a deal (current QTD vs same days of prev / prev-year quarter).
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
let dealPage=1, dealQuery='';
function dealFiltered(){{
  let list=DEALS.filter(e=>dspSetMatch(e.advSet));
  if(!dealQuery) return list;
  const q=dealQuery.toLowerCase();
  return list.filter(e=>String(e.clearvu??'').toLowerCase().includes(q)
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
  document.getElementById('deal-body').innerHTML = slice.map(e=>
    `<tr><td class="sticky-col colw-cv" title="${{escapeHtml(e.clearvu)}}">${{e.clearvu!=null?escapeHtml(e.clearvu):'<span class="muted">—</span>'}}</td>`+
    `<td class="sticky-col colw-ad" title="${{escapeHtml(e.ad_name)}}">${{e.ad_name!=null?escapeHtml(e.ad_name):'<span class="muted">—</span>'}}</td>`+
    `<td class="sticky-col colw-id" title="${{escapeHtml(e.deal_id)}}">${{(e.deal_id&&e.deal_id!=='nan')?escapeHtml(e.deal_id):'<span class="muted">—</span>'}}</td>`+
    QUARTERS.map(q=>e.rev[q]!=null?`<td class="number" title="${{fmtUSD2(e.rev[q])}}">${{fmtUSDc(e.rev[q])}}</td>`:'<td class="number muted">·</td>').join('')+
    `<td class="number" style="font-weight:600">${{fmtUSD(e.total)}}</td>`+
    (e.qtdCur!=null?`<td class="number grp-start" title="${{fmtUSD2(e.qtdCur)}}">${{fmtUSDc(e.qtdCur)}}</td>`:'<td class="number grp-start muted">·</td>')+
    pctCell(dealGrowth(e,'qtdPrevQ'))+
    pctCell(dealGrowth(e,'qtdPrevY'))+
    '</tr>').join('')
    || '<tr><td class="muted" colspan="'+(7+QUARTERS.length)+'">No matching deals</td></tr>';
  const totalRev=list.reduce((s,e)=>s+e.total,0);
  document.getElementById('deal-count').textContent =
    `${{fmtInt(list.length)}} deals · ${{fmtUSD(totalRev)}}${{dealQuery?' (filtered)':''}}`;
  renderPagination('deal-pag',pages,dealPage,p=>{{dealPage=p;renderDeals();}});
}}
function dealSearch(q){{ dealQuery=q.trim(); dealPage=1; renderDeals(); }}
function dealCSV(){{
  const list=dealFiltered();
  const header=['ClearVu Account','Ad Name','Deal ID',...QUARTERS.map(fmtQ),'Total','QTD (USD)','QoQ %','YoY %'];
  const body=list.map(e=>{{
    const qoq=dealGrowth(e,'qtdPrevQ'), yoy=dealGrowth(e,'qtdPrevY');
    return [e.clearvu??'',e.ad_name??'',e.deal_id??'',...QUARTERS.map(q=>e.rev[q]??0),e.total,
            e.qtdCur??'', qoq!=null?(qoq*100).toFixed(1)+'%':'', yoy!=null?(yoy*100).toFixed(1)+'%':''];
  }});
  downloadCSV([header,...body],'adex_deals');
}}

// ══════════════ Tab 3: Open Auction (ad_name × quarter, Beachfront) ══════════════
const OA = (()=>{{
  const map=new Map();
  OA_ROWS.forEach(r=>{{
    const key=r.ad_name??'—';
    let e=map.get(key);
    if(!e){{e={{ad_name:r.ad_name,advSet:new Set(),rev:{{}},total:0,qtdCur:null,qtdPrevQ:null,qtdPrevY:null}};map.set(key,e);}}
    const q=String(r.quarter).slice(0,10);
    const v=Number(r.rev_gross)||0;
    if(r.advertiser!=null) e.advSet.add(r.advertiser);
    e.rev[q]=(e.rev[q]||0)+v; e.total+=v;
    e.qtdCur=addN(e.qtdCur, r.rev_qtd_current!=null?Number(r.rev_qtd_current):null);
    e.qtdPrevQ=addN(e.qtdPrevQ, r.rev_qtd_prev_qtd!=null?Number(r.rev_qtd_prev_qtd):null);
    e.qtdPrevY=addN(e.qtdPrevY, r.rev_qtd_prev_year!=null?Number(r.rev_qtd_prev_year):null);
  }});
  return [...map.values()].sort((a,b)=>b.total-a.total);   // rev_gross DESC
}})();

// ══════════════ Global DSP filter (applies to all tabs) ══════════════
// Options sorted by deals revenue (OA-only DSPs appended alphabetically).
const DSP_FILTER_LIST=(()=>{{
  const seen=new Set(), list=[];
  DSP.forEach(e=>{{ if(e.advertiser!=null&&!seen.has(e.advertiser)){{seen.add(e.advertiser);list.push(e.advertiser);}} }});
  const extra=new Set();
  OA.forEach(e=>e.advSet.forEach(a=>{{ if(!seen.has(a)) extra.add(a); }}));
  return list.concat([...extra].sort((a,b)=>String(a).localeCompare(String(b))));
}})();
const selectedDSP=new Set();
const dspMatch=a=>selectedDSP.size===0||selectedDSP.has(a);
const dspSetMatch=s=>selectedDSP.size===0||[...s].some(a=>selectedDSP.has(a));

function msToggle(){{
  document.getElementById('dsp-filter-dd').classList.toggle('open');
  document.getElementById('dsp-filter-trigger').classList.toggle('open');
}}
document.addEventListener('click',e=>{{ if(!e.target.closest('.ms-wrap')){{
  document.getElementById('dsp-filter-dd').classList.remove('open');
  document.getElementById('dsp-filter-trigger').classList.remove('open');
}} }});
function msSearch(q){{
  q=q.toLowerCase();
  document.querySelectorAll('#dsp-filter-options .ms-option').forEach(o=>{{
    o.style.display=(!q||o.dataset.val.toLowerCase().includes(q))?'':'none';
  }});
}}
function buildDspFilter(){{
  document.getElementById('dsp-filter-options').innerHTML = DSP_FILTER_LIST.map(a=>
    `<label class="ms-option" data-val="${{escapeHtml(a)}}">
       <input type="checkbox" ${{selectedDSP.has(a)?'checked':''}} onchange="dspFilterPick('${{encodeURIComponent(a)}}',this.checked)">
       <span title="${{escapeHtml(a)}}">${{escapeHtml(a)}}</span>
     </label>`).join('');
}}
function dspFilterPick(enc,on){{
  const a=decodeURIComponent(enc);
  if(on) selectedDSP.add(a); else selectedDSP.delete(a);
  dspFilterApply();
}}
function dspFilterClear(){{
  selectedDSP.clear(); buildDspFilter();
  document.getElementById('dsp-filter-search').value=''; msSearch('');
  dspFilterApply();
}}
function dspFilterApply(){{
  const lbl=document.getElementById('dsp-filter-label');
  lbl.textContent=selectedDSP.size===0?'All DSPs':(selectedDSP.size===1?[...selectedDSP][0]:selectedDSP.size+' DSPs selected');
  document.getElementById('dsp-filter-trigger').classList.toggle('active-filter',selectedDSP.size>0);
  dspPage=dealPage=oaPage=1;
  renderDsp(); renderDeals(); renderOA();
}}

const OA_PAGE=50;
let oaPage=1, oaQuery='';
function oaFiltered(){{
  let list=OA.filter(e=>dspSetMatch(e.advSet));
  if(!oaQuery) return list;
  const q=oaQuery.toLowerCase();
  return list.filter(e=>String(e.ad_name??'').toLowerCase().includes(q));
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
    `${{fmtInt(list.length)}} ad names · ${{fmtUSD(totalRev)}}${{oaQuery?' (filtered)':''}}`;
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
  downloadCSV([header,...body],'adex_open_auction');
}}

// boot
document.addEventListener('DOMContentLoaded',()=>{{
  buildDspFilter();
  renderDsp();
  renderDeals();
  renderOA();
}});
</script>
</body>
</html>"""
