# Paired-check fault matrix: migration-check-author (blind, Sonnet)

Generated 2026-10-21 01:10 UTC by `python -m faults.pair_matrix` on `/private/tmp/claude-501/-Users-chet-dev-projects-snowflake-data-project/2a494b27-de92-4401-b6ce-43d5b517e64c/scratchpad/blind-mig/proposals/migration-check-author/checks` (17 checks).

**False alarms on clean data: 0/17**

**Faults detected: 10/12** (by at least one check failing that passed on clean data).

| Fault | Table | Checks that failed |
|---|---|---|
| `drop_rows` | payment | `payment_column_aggregates`, `payment_monthly_counts`, `payment_row_count`, `payment_row_hash` |
| `truncate_strings` | film | `film_column_aggregates`, `film_row_hash` |
| `shift_timestamps_tz` | rental | `rental_column_aggregates`, `rental_monthly_counts`, `rental_row_hash` |
| `perturb_decimal` | payment | `payment_column_aggregates`, `payment_row_hash` |
| `null_out_column` | customer | `customer_column_aggregates`, `customer_row_hash` |
| `duplicate_rows` | rental | `rental_column_aggregates`, `rental_monthly_counts`, `rental_row_count`, `rental_row_hash` |
| `swap_fk_values` | rental | `rental_row_hash` |
| `orphan_fk` | payment | `payment_column_aggregates`, `payment_row_hash` |
| `trailing_whitespace` | film | `film_column_aggregates`, `film_row_hash` |
| `truncate_microseconds` | payment | `payment_column_aggregates`, `payment_row_hash` |
| `drop_check_constraint` | film | **none: MISSED** |
| `tiny_vector_drift` | film_embedding | **none: MISSED** |
