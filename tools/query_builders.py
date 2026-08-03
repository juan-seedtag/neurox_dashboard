"""SQL query builders for both dashboard sections."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

SQL_DIR = Path(__file__).resolve().parent.parent / "sql"

VALID_DIMENSIONS = {
    "dsp_group_name",
    "connection_type",
    "product_category",
    "business_line",
    "publisher_country",
    "channel_id",
    "clearvu_account",
}
VALID_GRAINS = {"day", "week", "month", "quarter", "year"}


def _check_dims(*dims: str) -> None:
    """Reject unknown dimensions (raises even under `python -O`, unlike assert)."""
    for d in dims:
        if d not in VALID_DIMENSIONS:
            raise ValueError(f"Invalid dimension: {d!r} (valid: {sorted(VALID_DIMENSIONS)})")


def _check_grain(grain: str) -> None:
    if grain not in VALID_GRAINS:
        raise ValueError(f"Invalid grain: {grain!r} (valid: {sorted(VALID_GRAINS)})")


def grain_to_trunc(grain: str) -> str:
    """Map grain to a SQL date_trunc expression over the `date` column."""
    grains = {
        "day": "DATE_TRUNC('day', date)",
        "week": "DATE_TRUNC('week', date)",
        "month": "DATE_TRUNC('month', date)",
        "quarter": "DATE_TRUNC('quarter', date)",
        "year": "DATE_TRUNC('year', date)",
    }
    return grains.get(grain, "DATE_TRUNC('day', date)")


@lru_cache(maxsize=1)
def _consolidated_base() -> str:
    """The sofia base file — already a full `WITH consolidated_demand AS (...)`."""
    return (SQL_DIR / "consolidated_demand_base.sql").read_text(encoding="utf-8")


def _sql_str(value: str) -> str:
    """Escape a string literal for safe inlining into SQL."""
    return "'" + str(value).replace("'", "''") + "'"


def _dsp_and(dsp: str | None) -> str:
    """Optional `AND dsp_group_name = '<dsp>'` predicate for Section-1 queries."""
    return f"  AND dsp_group_name = {_sql_str(dsp)}" if dsp else ""


def _filters_and(filters: dict | None) -> str:
    """Optional `AND <dim> IN (...)` predicates for the Overview dimension filters."""
    if not filters:
        return ""
    parts = []
    for dim, vals in filters.items():
        if dim in VALID_DIMENSIONS and vals:
            inlist = ", ".join(_sql_str(v) for v in vals)
            parts.append(f"  AND {dim} IN ({inlist})")
    return "\n".join(parts)


def dsp_universe_query(date_from: str, date_to: str) -> str:
    """List every DSP with gross revenue in the window, highest first."""
    return f"""{_consolidated_base()}
SELECT dsp_group_name, SUM(revenue_gross) AS revenue_gross
FROM consolidated_demand
WHERE date >= DATE {_sql_str(date_from)} AND date <= DATE {_sql_str(date_to)}
  AND dsp_group_name IS NOT NULL
GROUP BY 1
ORDER BY revenue_gross DESC
LIMIT 10000
"""


def all_dsp_chart_query(dimension: str, date_from: str, date_to: str) -> str:
    """Month-grain revenue for EVERY DSP split by one dimension (for the embedded,
    server-free overview). Returns: period, dsp_group_name, <dimension>, revenue_gross."""
    _check_dims(dimension)
    return f"""{_consolidated_base()}
SELECT
    DATE_TRUNC('month', date) AS period,
    dsp_group_name,
    {dimension} AS {dimension},
    SUM(revenue_gross) AS revenue_gross
FROM consolidated_demand
WHERE date >= DATE {_sql_str(date_from)} AND date <= DATE {_sql_str(date_to)}
  AND dsp_group_name IS NOT NULL
GROUP BY 1, 2, 3
LIMIT 5000000
"""


def all_dsp_table_query(dim1: str, dim2: str, date_from: str, date_to: str) -> str:
    """Month-grain two-dimension breakdown for EVERY DSP.
    Returns: period, dsp_group_name, <dim1>, <dim2>, revenue_gross."""
    _check_dims(dim1, dim2)
    sel = f"    {dim1} AS {dim1}," if dim1 == dim2 else f"    {dim1} AS {dim1},\n    {dim2} AS {dim2},"
    gb = "1, 2, 3" if dim1 == dim2 else "1, 2, 3, 4"
    return f"""{_consolidated_base()}
SELECT
    DATE_TRUNC('month', date) AS period,
    dsp_group_name,
{sel}
    SUM(revenue_gross) AS revenue_gross
FROM consolidated_demand
WHERE date >= DATE {_sql_str(date_from)} AND date <= DATE {_sql_str(date_to)}
  AND dsp_group_name IS NOT NULL
GROUP BY {gb}
LIMIT 5000000
"""


def time_evolution_chart_query(
    grain: str, dimension: str, date_from: str, date_to: str,
    dsp: str | None = None, filters: dict | None = None,
) -> str:
    """
    Section 1 chart: revenue over time, split by a single dimension, optionally
    scoped to one DSP and filtered by dimension-value sets. Returns rows of:
    period, <dimension>, revenue_gross.
    """
    _check_grain(grain)
    _check_dims(dimension)
    return f"""{_consolidated_base()}
SELECT
    {grain_to_trunc(grain)} AS period,
    {dimension} AS {dimension},
    SUM(revenue_gross) AS revenue_gross
FROM consolidated_demand
WHERE date >= DATE {_sql_str(date_from)} AND date <= DATE {_sql_str(date_to)}
{_dsp_and(dsp)}
{_filters_and(filters)}
GROUP BY 1, 2
ORDER BY period DESC, revenue_gross DESC
LIMIT 1000000
"""


def time_evolution_table_query(
    grain: str, dim1: str, dim2: str, date_from: str, date_to: str,
    dsp: str | None = None, filters: dict | None = None,
) -> str:
    """
    Section 1 table: revenue over time broken down by two dimensions, optionally
    scoped to one DSP and filtered. Returns rows of: period, <dim1>, <dim2>, revenue_gross.
    """
    _check_grain(grain)
    _check_dims(dim1, dim2)
    # Trino only accepts ordinals/expressions in GROUP BY (not SELECT aliases).
    if dim2 == dim1:
        select_dims = f"    {dim1} AS {dim1},"
        group_by = "1, 2"
    else:
        select_dims = f"    {dim1} AS {dim1},\n    {dim2} AS {dim2},"
        group_by = "1, 2, 3"
    return f"""{_consolidated_base()}
SELECT
    {grain_to_trunc(grain)} AS period,
{select_dims}
    SUM(revenue_gross) AS revenue_gross
FROM consolidated_demand
WHERE date >= DATE {_sql_str(date_from)} AND date <= DATE {_sql_str(date_to)}
{_dsp_and(dsp)}
{_filters_and(filters)}
GROUP BY {group_by}
ORDER BY period DESC, revenue_gross DESC
LIMIT 1000000
"""


def dsp_details_query(
    dsp: str | None,
    date_from: str,
    date_to: str,
    min_deals: int = 25,
    coverage: float = 0.995,
    max_deals: int = 2000,
) -> str:
    """
    Section 2: deal/advertiser-level detail (PMP / Curation / Open Auction),
    unioning Beachfront (bfm_demand) and Seedtag O&O SSP (etl_ssp_responses_daily_enriched).

    ALL deals are represented: deals are kept as individual rows until `coverage`
    of each deal_type's revenue is reached (at least `min_deals`, at most
    `max_deals` per deal_type); the remainder comes back as one aggregated
    "long tail" row per month (is_tail=TRUE, tail_deals=count), so per-deal_type
    totals reconcile exactly.

    When `dsp` is None/empty the DSP predicate is dropped (returns all DSPs in one
    scan) — used for the embedded build; the live server passes a specific DSP.
    """
    if not 0 < coverage <= 1:
        raise ValueError(f"coverage must be in (0, 1], got {coverage}")
    template = (SQL_DIR / "dsp_details.sql").read_text(encoding="utf-8")
    if dsp:
        lit = _sql_str(dsp)
        bfm_dsp_and = f"AND COALESCE(m.dsp_label, a.advertiser) = {lit}"
        ssp_dsp_and = f"AND s.dsp_group_name = {lit}"
    else:
        bfm_dsp_and = ""
        ssp_dsp_and = ""
    return template.format(
        date_from=date_from,
        date_to=date_to,
        bfm_dsp_and=bfm_dsp_and,
        ssp_dsp_and=ssp_dsp_and,
        min_deals=int(min_deals),
        coverage=float(coverage),
        max_deals=int(max_deals),
    )
