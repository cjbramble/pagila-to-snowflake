# Fault detection matrix

Generated 2026-10-20 20:37 UTC by `python -m faults.matrix`. Baseline suite before faults: all passed.

**Mutation score: 12/12 (100%)** faults detected by at least one layer.

Cells show how many tests in that layer failed; `·` means the layer didn't notice.

| Fault | Table | schema | volume | process | aggregate | row | integrity | contract | Detected |
|---|---|---|---|---|---|---|---|---|---|
| `drop_rows` | payment | · | 1 | · | 1 | 1 | · | · | yes |
| `truncate_strings` | film | · | · | · | 1 | 1 | · | · | yes |
| `shift_timestamps_tz` | rental | · | · | · | 1 | 1 | · | · | yes |
| `perturb_decimal` | payment | · | · | · | 1 | 1 | · | · | yes |
| `null_out_column` | customer | · | · | · | 1 | 1 | · | · | yes |
| `duplicate_rows` | rental | · | 1 | · | 1 | 1 | · | 1 | yes |
| `swap_fk_values` | rental | · | · | · | · | 1 | · | · | yes |
| `orphan_fk` | payment | · | · | · | 1 | 1 | 1 | · | yes |
| `trailing_whitespace` | film | · | · | · | · | 1 | · | · | yes |
| `truncate_microseconds` | payment | · | · | · | 1 | 1 | · | · | yes |
| `drop_check_constraint` | film | 1 | · | · | · | · | 1 | · | yes |
| `tiny_vector_drift` | film_embedding | · | · | · | · | 1 | · | · | yes |

## Faults

- `drop_rows`: 3 payments silently not loaded
- `truncate_strings`: description cut to 100 characters, as by a too-narrow VARCHAR
- `shift_timestamps_tz`: rental_date read as America/Los_Angeles wall-clock instead of UTC (+7h)
- `perturb_decimal`: one payment amount off by a cent
- `null_out_column`: email lost for 5 customers
- `duplicate_rows`: 2 rentals loaded twice, as by a retried batch
- `swap_fk_values`: customer_id swapped between two rentals
- `orphan_fk`: one payment points at a rental that doesn't exist
- `trailing_whitespace`: one title gains a trailing space
- `truncate_microseconds`: payment_date loses sub-millisecond precision
- `drop_check_constraint`: the rating CHECK constraint (decision D08) is missing from the target
- `tiny_vector_drift`: one embedding element drifts by 1e-7
