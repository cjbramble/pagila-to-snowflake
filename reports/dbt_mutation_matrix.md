# dbt mutation matrix: merged suite (existing + promoted dbt-test-author tests)

Generated 2026-10-21 00:45 UTC by `python -m faults.dbt_mutations` on `/Users/chet/dev-projects/snowflake-data-project/dbt`.

**Kill score: 17/17** mutations caught by at least one test (unit tests alone: 17, data tests alone: 13).

Cells list the failing tests; `·` means none noticed.

| Mutation | Model | Rule | Unit tests | Data tests | Verdict |
|---|---|---|---|---|---|
| `rr_floor_days` | mart_rental_returns | ETL-006 | `late_return_rules`, `rental_returns_boundaries` | `assert_late_fee_matches_basis`, `mart_rental_returns_matches_rules` | killed |
| `rr_ceil_decimal_division` | mart_rental_returns | ETL-006 | `rental_returns_boundaries` | · | killed |
| `rr_datediff_seconds` | mart_rental_returns | ETL-006 | `late_return_rules`, `rental_returns_boundaries` | · | killed |
| `rr_due_exact_is_late` | mart_rental_returns | ETL-005 | `late_return_rules`, `rental_returns_boundaries` | `assert_late_fee_matches_basis`, `mart_rental_returns_matches_rules` | killed |
| `rr_replacement_at_2x` | mart_rental_returns | ETL-007 | `late_return_rules`, `rental_returns_boundaries` | `assert_late_fee_matches_basis`, `mart_rental_returns_matches_rules` | killed |
| `rr_replacement_plus_daily` | mart_rental_returns | ETL-007 | `late_return_rules`, `rental_returns_boundaries` | `assert_late_fee_matches_basis`, `mart_rental_returns_matches_rules` | killed |
| `rr_never_returned_none` | mart_rental_returns | ETL-007 | `late_return_rules`, `rental_returns_boundaries`, `rental_returns_no_fanout_or_drop` | `assert_late_fee_matches_basis`, `mart_rental_returns_matches_rules` | killed |
| `rr_due_off_by_one` | mart_rental_returns | ETL-004 | `late_return_rules`, `rental_returns_boundaries`, `rental_returns_no_fanout_or_drop` | `mart_rental_returns_matches_rules` | killed |
| `rr_due_not_utc` | mart_rental_returns | ETL-004 | `late_return_rules`, `rental_returns_boundaries`, `rental_returns_no_fanout_or_drop` | `mart_rental_returns_matches_rules`, `mart_rental_returns_outputs_utc` | killed |
| `rev_local_month` | mart_monthly_store_revenue | ETL-002 | `monthly_revenue_rules`, `monthly_store_revenue_utc_buckets` | · | killed |
| `rev_staff_attribution` | mart_monthly_store_revenue | ETL-001 | `monthly_revenue_rules`, `monthly_store_revenue_utc_buckets`, `monthly_store_revenue_zero_only_month_kept` | · | killed |
| `rev_drop_zero_amount` | mart_monthly_store_revenue | ETL-002 | `monthly_revenue_rules`, `monthly_store_revenue_utc_buckets`, `monthly_store_revenue_zero_only_month_kept` | `assert_revenue_attributes_every_payment` | killed |
| `rev_sum_distinct` | mart_monthly_store_revenue | ETL-002 | `monthly_store_revenue_utc_buckets` | `assert_revenue_attributes_every_payment` | killed |
| `clv_no_coalesce` | mart_customer_lifetime_value | ETL-003 | `customer_lifetime_value_rules`, `customer_ltv_aggregates` | `not_null_mart_customer_lifetime_value_lifetime_revenue` | killed |
| `clv_rentals_from_payments` | mart_customer_lifetime_value | ETL-003 | `customer_lifetime_value_rules`, `customer_ltv_aggregates` | `mart_customer_lifetime_value_matches_source` | killed |
| `clv_first_is_max` | mart_customer_lifetime_value | ETL-003 | `customer_lifetime_value_rules`, `customer_ltv_aggregates` | `mart_customer_lifetime_value_matches_source` | killed |
| `clv_inner_join` | mart_customer_lifetime_value | ETL-003 | `customer_lifetime_value_rules`, `customer_ltv_aggregates` | `assert_lifetime_value_matches_payments`, `mart_customer_lifetime_value_matches_source` | killed |

## Mutations

- `rr_floor_days`: days late rounded down instead of up
- `rr_ceil_decimal_division`: days late via ceil(micros / 86400000000): the quotient keeps 6 decimals, so up to ~43 ms past a day boundary isn't counted (the real bug dbt-test-author found)
- `rr_datediff_seconds`: lateness measured with DATEDIFF(second), which counts boundaries
- `rr_due_exact_is_late`: returned exactly at due_at counts as late
- `rr_replacement_at_2x`: exactly 2x overdue already charged replacement
- `rr_replacement_plus_daily`: replacement cost added to the daily fee instead of replacing it
- `rr_never_returned_none`: never-returned rentals get fee basis 'none' (fee 0.00) instead of null
- `rr_due_off_by_one`: due date one day early
- `rr_due_not_utc`: due_at computed in Los Angeles time (same instant, non-UTC output)
- `rev_local_month`: months bucketed in Los Angeles time instead of UTC
- `rev_staff_attribution`: revenue credited by the rental's staff_id instead of the inventory's store
- `rev_drop_zero_amount`: zero-amount payments excluded
- `rev_sum_distinct`: revenue summed over distinct amounts
- `clv_no_coalesce`: customers without payments get null lifetime revenue instead of 0.00
- `clv_rentals_from_payments`: rental_count counts payments
- `clv_first_is_max`: first_payment_at takes the latest payment
- `clv_inner_join`: customers without payments dropped
