-- =============================================================================
-- Weekly View — feeds the Weekly View tab (WoW rolling windows)
-- =============================================================================
-- Same shape as sofia's weekly-revenue-report WoW query (rolling 7-day windows,
-- not ISO calendar weeks), on the curated reporting_adex_demand table:
--   current_week  = [current_date - 7 days, current_date)
--   previous_week = [current_date - 14 days, current_date - 7 days)
-- NeuroX scope, consistent with the Commercial Activity tab: no Reseller, no
-- Direct / External business lines, Conversant-via-Conversant → Direct.
-- The report groups client-side by any ordered combination of business_line,
-- connection_type, product_category, dsp_group_name and clearvu_account
-- (user-selectable segments), computing WoW USD / % variation sorted by USD
-- variation desc. channel_id is kept in the grain for the global filters.
--
-- No placeholders — the windows anchor on current_date at query time.
-- =============================================================================

SELECT
    CASE
        WHEN date >= current_date - INTERVAL '7' DAY
         AND date <  current_date THEN 'current_week'
        WHEN date >= current_date - INTERVAL '14' DAY
         AND date <  current_date - INTERVAL '7' DAY THEN 'previous_week'
    END AS period
    , CASE
        WHEN dsp_group_name = 'Conversant' AND channel_id = 'Conversant' THEN 'Direct'
        ELSE connection_type
      END AS connection_type
    , business_line
    , product_category
    , dsp_group_name
    , clearvu_account
    , channel_id
    , SUM(revenue_gross) AS rev_gross
FROM reporting_adex_demand
WHERE 1=1
  AND connection_type <> 'Reseller'
  AND business_line NOT LIKE '%Direct%'
  AND business_line NOT LIKE '%External%'
  AND date >= current_date - INTERVAL '14' DAY
  AND date <  current_date
GROUP BY 1, 2, 3, 4, 5, 6, 7
HAVING SUM(revenue_gross) > 0
ORDER BY rev_gross DESC
