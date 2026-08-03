-- =============================================================================
-- Commercial Activity — feeds Tab 1 (NeuroX overview pivot)
-- =============================================================================
-- NeuroX scope on the curated reporting_adex_demand table (fast, closing-grade):
--   * connection_type <> 'Reseller'
--   * business_line NOT LIKE '%Direct%'
--   * Conversant via the Conversant channel is re-labelled Direct.
-- Quarter grain; the report pivots client-side into
--   columns = business_line × quarter (current partial quarter = "pacing"),
--   rows = dsp_group_name × connection_type × product_category (+ TOTAL rows),
--   values = revenue_gross, with row and column totals.
-- channel_id is kept in the grain to power the global Channel ID filter.
--
-- Placeholders: {date_from} (ISO date, inclusive), {build_date} (ISO date,
-- exclusive upper bound — today's partial day is excluded).
-- =============================================================================

SELECT
    CAST(date_trunc('quarter', date) AS date) AS quarter
    , CASE
        WHEN dsp_group_name = 'Conversant' AND channel_id = 'Conversant' THEN 'Direct'
        ELSE connection_type
      END AS connection_type
    , business_line
    , product_category
    , dsp_group_name
    , channel_id
    , SUM(revenue_gross) AS rev_gross
    , SUM(total_impressions) AS impressions
FROM reporting_adex_demand
WHERE 1=1
  AND connection_type <> 'Reseller'
  AND business_line NOT LIKE '%Direct%'
  AND business_line NOT LIKE '%External%'
  AND date >= DATE '{date_from}'
  AND date < DATE '{build_date}'
GROUP BY 1, 2, 3, 4, 5, 6
HAVING SUM(revenue_gross) > 0
ORDER BY rev_gross DESC
