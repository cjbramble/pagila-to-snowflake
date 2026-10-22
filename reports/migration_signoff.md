# Migration sign-off: Pagila → Snowflake

Generated 2026-10-22 01:10 UTC by `python -m reconcile.signoff` at commit `90f31b9`.

## Recommendation: **GO**

Every gate criterion is met.

| Gate | Criterion | Met | Detail |
|---|---|---|---|
| G1 | Every requirement is covered by at least one test that ran | yes | 17/17 covered |
| G2 | Every requirement passes, or has an approved, unexpired waiver | yes | no failing or incomplete requirements |
| G3 | Every known source issue is accepted by a named human | yes | 5/5 accepted |
| G4 | The run is on committed code, so the report traces to one commit | yes | clean tree |
| G5 | Every test that traces to no requirement passes, and none declares an unknown one | yes | all pass |

## Scope

- **Source:** PostgreSQL 18.6, database `pagila`, schema `public` (Pagila).
- **Target:** Snowflake `PAGILA_MIG.RAW`.
- **Migrated:** 16 tables, 93 columns (1 excluded by decision); 8 source views are not migrated.
- **Mapping decisions:** 9/9 decided by the human (`mapping/type_mapping.yml`).
- **Transformed:** 3 dbt marts: `mart_customer_lifetime_value`, `mart_monthly_store_revenue`, `mart_rental_returns`.
- **Requirements:** 9 migration (MIG), 8 business rule (ETL); `requirements/requirements.yml`.

## Run summary

| Suite | Result |
|---|---|
| Load (`QA.LOAD_LOG`, latest per table) | 16/16 tables SUCCESS with rows loaded = rows extracted; 122,209 rows |
| pytest | 195/195 passed |
| dbt test | 29/29 passed (8 unit, 21 data) |

## Requirement status and traceability

Test names are pytest functions (with passed/total over their parameters) and dbt tests.

| Requirement | Title | Status | pytest | dbt |
|---|---|---|---|---|
| MIG-001 | Mapping spec covers the source | PASS | `test_columns_are_well_formed` 1/1<br>`test_every_source_column_is_mapped` 1/1<br>`test_every_source_relation_is_mapped_or_excluded` 1/1<br>`test_no_open_decisions` 1/1<br>`test_primary_keys_reference_mapped_columns` 1/1 | · |
| MIG-002 | Target schema matches the spec | PASS | `test_columns_match_spec` 16/16<br>`test_primary_key_matches_spec` 16/16<br>`test_raw_contains_exactly_the_spec_tables` 1/1 | · |
| MIG-003 | Row counts match | PASS | `test_pair_results_match` 7/7<br>`test_row_counts_match` 16/16 | · |
| MIG-004 | Column aggregates match | PASS | `test_column_aggregates_match` 16/16<br>`test_pair_results_match` 5/5 | · |
| MIG-005 | Row content matches | PASS | `test_generator_reproduces_handwritten_payment_hashes` 1/1<br>`test_pair_results_match` 5/5<br>`test_row_hashes_match` 16/16 | · |
| MIG-006 | Load run is complete and logged | PASS | `test_latest_load_of_every_table_succeeded` 1/1<br>`test_table_still_holds_logged_rows` 16/16 | · |
| MIG-007 | Referential integrity holds in the target | PASS | `test_no_orphans_in_target` 23/23 | · |
| MIG-008 | Source domain rules hold in the target | PASS | `test_film_check_constraints_exist` 1/1<br>`test_film_domain_rules_hold` 1/1 | · |
| MIG-009 | Target data contracts pass | PASS | `test_soda_contract_passes` 4/4 | · |
| ETL-001 | Revenue is attributed to the inventory's store | PASS | `test_monthly_store_revenue_matches_source` 1/1<br>`test_store_totals_match_legacy_sales_by_store_view` 1/1 | `assert_revenue_attributes_every_payment` 1/1<br>`monthly_revenue_rules` 1/1<br>`monthly_store_revenue_utc_buckets` 1/1<br>`not_null_mart_monthly_store_revenue_store_id` 1/1<br>`relationships_mart_monthly_store_revenue_store_id__store_id__ref_stg_store_` 1/1 |
| ETL-002 | Monthly revenue by store | PASS | `test_monthly_store_revenue_matches_source` 1/1 | `assert_monthly_revenue_grain_is_unique` 1/1<br>`assert_revenue_attributes_every_payment` 1/1<br>`monthly_revenue_rules` 1/1<br>`monthly_store_revenue_utc_buckets` 1/1<br>`monthly_store_revenue_zero_only_month_kept` 1/1<br>`not_null_mart_monthly_store_revenue_payment_count` 1/1<br>`not_null_mart_monthly_store_revenue_revenue_month` 1/1 |
| ETL-003 | Customer lifetime value | PASS | `test_customer_lifetime_value_matches_source` 1/1 | `assert_lifetime_value_matches_payments` 1/1<br>`customer_lifetime_value_rules` 1/1<br>`customer_ltv_aggregates` 1/1<br>`mart_customer_lifetime_value_matches_source` 1/1<br>`not_null_mart_customer_lifetime_value_customer_id` 1/1<br>`not_null_mart_customer_lifetime_value_lifetime_revenue` 1/1<br>`relationships_mart_customer_lifetime_value_customer_id__customer_id__ref_stg_customer_` 1/1<br>`unique_mart_customer_lifetime_value_customer_id` 1/1 |
| ETL-004 | Rental due date | PASS | `test_rental_returns_match_source` 1/1 | `late_return_rules` 1/1<br>`mart_rental_returns_outputs_utc` 1/1<br>`not_null_mart_rental_returns_due_at` 1/1<br>`rental_returns_boundaries` 1/1<br>`rental_returns_no_fanout_or_drop` 1/1 |
| ETL-005 | Return status | PASS | `test_rental_returns_match_source` 1/1 | `accepted_values_mart_rental_returns_return_status__on_time__late__not_returned` 1/1<br>`assert_every_rental_classified` 1/1<br>`late_return_rules` 1/1<br>`not_null_mart_rental_returns_rental_id` 1/1<br>`not_null_mart_rental_returns_return_status` 1/1<br>`rental_returns_boundaries` 1/1<br>`rental_returns_no_fanout_or_drop` 1/1<br>`unique_mart_rental_returns_rental_id` 1/1 |
| ETL-006 | Days late | PASS | `test_rental_returns_match_source` 1/1 | `assert_late_fee_matches_basis` 1/1<br>`late_return_rules` 1/1<br>`rental_returns_boundaries` 1/1 |
| ETL-007 | Late fee | PASS | `test_rental_returns_match_source` 1/1 | `accepted_values_mart_rental_returns_fee_basis__none__daily__replacement__not_returned` 1/1<br>`assert_late_fee_matches_basis` 1/1<br>`late_return_rules` 1/1<br>`rental_returns_boundaries` 1/1 |
| ETL-008 | Mart data contracts pass | PASS | `test_mart_contract_passes` 3/3 | · |

## Known source issues

Source data-quality findings that migrate faithfully. Each needs a human disposition (`requirements/signoff.yml`).

| Issue | Title | Disposition | Decided by |
|---|---|---|---|
| SRC-001 | Payments dated before their rental | accepted | Chet |
| SRC-002 | Zero-amount payments | accepted | Chet |
| SRC-003 | Credential hashes migrated | accepted | Chet |
| SRC-004 | Store managers belong to other stores | accepted | Chet |
| SRC-005 | Payments made by someone other than the renter | accepted | Chet |

## Waivers

None.

## Supporting evidence

Not re-run here; each report states when it was generated.

- [`reports/fault_matrix.md`](fault_matrix.md): Mutation score: 12/12 (100%) (2026-10-22 01:10 UTC)
- [`reports/dbt_mutation_matrix.md`](dbt_mutation_matrix.md): Kill score: 17/17 (2026-10-21 00:54 UTC)
- [`AI_LOG.md`](../AI_LOG.md): defects found in AI-generated work and what caught them.
