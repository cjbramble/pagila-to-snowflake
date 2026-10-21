# dbt tests for the three marts

Files: `models/marts/_marts_tests.yml` (generic + unit tests), `tests/*.sql` (singular).

| Test | Rule | Bug it catches |
|---|---|---|
| unit `rental_returns_boundaries` | ETL-004..007 | wrong due date or duration; `<` vs `<=` at due_at; DATEDIFF second/day boundary counting; floor instead of ceil; 2x boundary off by one (`>=`); wrong replacement fee; non-null days/fee for unreturned; non-UTC offsets; fixed 1.00 fee; precision loss on sub-second lateness |
| unit `rental_returns_no_fanout_or_drop` | ETL-004, 005 | join fan-out or dropped rentals; wrong store attribution per inventory item |
| unit `monthly_store_revenue_utc_buckets` | ETL-001, 002 | local-time month bucketing at UTC month edges (+/- offsets); SUM(DISTINCT); dropped zero-amount payments; stores merged; multiple payments per rental |
| unit `monthly_store_revenue_zero_only_month_kept` | ETL-002 | zero-amount payments filtered out |
| unit `customer_ltv_aggregates` | ETL-003 | rental/payment fan-out; SUM(DISTINCT); inner join dropping customers; NULL instead of 0; first/last by local text instead of instant; non-UTC outputs |
| singular `mart_monthly_store_revenue_grain_unique` | ETL-002 | duplicate store-month rows |
| singular `mart_monthly_store_revenue_matches_payments` | ETL-001, 002 | any per-store-month divergence from an independent recompute on raw |
| singular `mart_monthly_store_revenue_totals_match_source` | ETL-001, 002 | orphaned or duplicated payments; total != raw total |
| singular `mart_customer_lifetime_value_matches_source` | ETL-003 | per-customer divergence in revenue, counts, first/last, store |
| singular `mart_customer_lifetime_value_totals` | ETL-003 | missing customers; totals not tying to payments/rentals |
| singular `mart_rental_returns_matches_rules` | ETL-004..007 | any divergence from an exact integer-microsecond recompute on real data |
| singular `mart_rental_returns_row_count` | ETL-004, 005 | dropped or duplicated rentals |
| singular `mart_rental_returns_column_consistency` | ETL-005..007 | status vs dates, days_late, fee_basis, late_fee contradictions |
| singular `mart_rental_returns_outputs_utc` | ETL-004 | due_at/rental_date/return_date left in the input offset |
| generic unique/not_null/relationships on keys | ETL-001..004 | grain, nulls, orphans |
| generic accepted_values on return_status, fee_basis | ETL-005, 007 | undeclared or missing status values |
| generic not_null on measures | ETL-002, 003 | NULL revenue/counts |

## Known failing test (suspected model bug)

`mart_rental_returns.rental_returns_boundaries` fails. `mart_rental_returns.sql` computes
`ceil(micros_after_due / 86400000000)`; Snowflake's decimal division keeps only 6 decimal
places, so a sub-0.5-microsecond fraction of a day is lost. Verified in Snowflake:
`ceil(1/86400000000)` = 0 (rental 3, 1 us late: days_late 0, fee 0.00, should be 1 / 1.00) and
`ceil((6*86400000000+1)/86400000000)` = 6 (rental 9, 2x + 1 us: days_late 6, should be 7).
Real data has whole-second timestamps, so the data tests pass; only the unit test sees it.
