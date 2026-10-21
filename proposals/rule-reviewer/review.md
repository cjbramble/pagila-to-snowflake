# Rule review: reporting marts draft (rules.md)

All counts from Postgres `public`, read-only. Source: rental 51,805; payment 51,061 (total $170,962.39); customer 999; store 500; staff 1,500. dq_checklist.md was not provided.

## 1. Which store does a payment belong to? (revenue by store)
- **Question:** Is a payment's store the paying staff's store, the customer's home store, or the store of the inventory item rented?
- **Why it matters:** payment has no store_id. The three routes disagree. Revenue per store changes completely.
- **Evidence:** joined payment-staff-customer-rental-inventory. staff.store_id <> customer.store_id on 51,061 of 51,061 rows (100%). staff vs inventory store differ on 51,061 (100%, $170,962.39 attributed differently). customer vs inventory differ on 25,466 (50%). Payments touch only 2 stores by every route, though store has 500 rows (498 never receive payment).
- **Options:** (a) inventory store (where the film physically was; recommended as the rental's location, and every payment has a rental); (b) staff store (who took the money); (c) customer home store. Human must pick; the choice is not derivable.

## 2. Late-day counting: partial days and the "late" threshold (late fees)
- **Question:** Is "days overdue" whole elapsed 24h periods (floor), rounded up (ceil), rounded, or calendar-date difference; and is a rental late as soon as it is 1 second past due, or only past the due date's calendar day?
- **Why it matters:** the same 27,750 late rentals give different fees.
- **Evidence:** timestamp-late (return_date > rental_date + duration days) = 27,750; calendar-date late = 22,552 (5,198 difference). Late by under 24h: 10,535 rentals. Fee sum for non-replacement late rentals: floor $30,244; round $42,496; ceil $57,788. Floor gives $0 for 10,535 rentals that are "late" yet owe nothing.
- **Options:** (a) ceil on timestamps (any started day counts; recommended as most consistent with "late"); (b) floor on elapsed time (full days only); (c) calendar-date difference, with the time zone fixed (see 6). Human decides.

## 3. Replacement-cost rule: replaces or adds, and the boundary
- **Question:** When a film is "more than rental_duration * 2 overdue", is the charge replacement_cost instead of the $1/day fee or in addition; and does the threshold mean overdue days > 2*duration, or total rental time > 2*duration?
- **Why it matters:** wording is ambiguous in both ways. "Overdue more than 2x duration" (overdue days > 2*d) is a much higher bar than "out longer than 2x duration" (return > rental + 2d, which is what I mean by a later reading below).
- **Evidence:** reading A (overdue > rental_duration*2 ... interpreted as elapsed since rental > 2*d): 1,827 rentals; 1 rental exactly equal at the 2x boundary (strict vs inclusive). By calendar dates: 1,484. Replacement cost total on those: $37,609.73; adding $1/day on top would add up to 9,738 more (ceil days). Under reading B (overdue days itself > 2*d, i.e. out > 3*d) the count is far smaller; I did not enumerate it, so it is not measured.
- **Options:** (a) replacement_cost only, replaces daily fee (recommended: otherwise the customer pays both); (b) add both; (c) cap at replacement_cost. Also state which reading of the threshold, and strict ">" as written.

## 4. Rentals never returned
- **Question:** What fee applies to rentals with NULL return_date: nothing, accrue to a report date, or replacement_cost?
- **Why it matters:** one implementation skips them (NULL comparison is false), another treats them as lost.
- **Evidence:** `count(*) where return_date is null` = 241; all 241 are already past due as of now(). Latest rental 2026-07-28; "as of" date is undefined.
- **Options:** (a) excluded from fees, listed as "open" (recommended; no invented as-of date); (b) accrue to a fixed as-of date; (c) replacement_cost after 2x threshold, needing an as-of date.

## 5. Payments vs fees: is the fee a computed figure or a payment, and does it relate to payment.amount?
- **Question:** Are late fees an informational computed column, or do they enter revenue and lifetime value; do they get reconciled against payments?
- **Why it matters:** revenue rules say "total payment amount" only, so fees would never appear in the marts. One engineer adds fees to revenue, another doesn't.
- **Evidence:** payments less than the film's rental_rate: 24 (zero amounts: 24 payments, see 9). Computed fees total roughly $30k-$58k plus up to $37.6k replacement vs $170,962.39 of payments (not reconcilable by data alone).
- **Options:** (a) fees are a separate mart column, not in revenue (recommended, matches the literal text); (b) add into revenue; (c) fee only for the policy report. Human decides.

## 6. Time zone for months, due dates, first/last payment dates
- **Question:** Which zone decides the month of a payment and the date of "first/last payment" and due dates?
- **Why it matters:** values are timestamptz (UTC; Snowflake TIMESTAMP_TZ +00:00). A store in another zone sees different months.
- **Evidence:** payments whose month differs between UTC and America/New_York: 324 of 51,061. Server is Etc/UTC; no store time zone column exists.
- **Options:** (a) UTC (recommended: only zone in the data); (b) a business zone, which the BA must name; (c) session zone, which is non-deterministic (avoid).

## 7. Multiple or zero payments per rental; rentals with no payment
- **Question:** Is payment the revenue unit even where a rental has 0 or 2 payments; does rentals count in lifetime value mean all rentals or only paid ones?
- **Why it matters:** joining rental to payment fans out or drops rows.
- **Evidence:** rentals with no payment: 749. Rentals with more than one payment: 1 (payment count 51,061 vs 51,056 distinct rental_id, 5 extras). Fee/revenue joins at rental grain would double-count that rental.
- **Options:** (a) count payments and rentals each from their own table, never joined (recommended); (b) join at rental grain, summing payments first; (c) count only paid rentals.

## 8. Lifetime value: customers with no payments or rentals; inactive customers
- **Question:** Do customers with zero payments appear (with 0 / NULL dates), and are inactive customers included?
- **Why it matters:** inner vs left join changes row count; SUM of nothing is NULL vs 0.
- **Evidence:** customers with no payment: 2; with no rental: 2; inactive (activebool false or active=0): 44. Customer count 999.
- **Options:** (a) all 999 customers, total 0 and NULL dates (recommended: keeps customer grain complete); (b) only customers with payments; (c) active only.

## 9. Zero-amount payments
- **Question:** Do zero-amount payments count in the payment count and the first/last payment dates?
- **Why it matters:** "how many payments" can be 24 higher; first/last dates may move.
- **Evidence:** `count(*) where amount=0` = 24; negatives 0. Of these, 2 are among payments dated before their rental (see 10).
- **Options:** (a) count them (recommended; they are recorded payments); (b) exclude from count and dates, keep in total.

## 10. Payments dated before the rental (events out of order)
- **Question:** Should payments with payment_date earlier than rental_date be kept, flagged, or re-dated?
- **Why it matters:** affects month attribution (payment month vs rental month) and first-payment date.
- **Evidence:** `payment_date < rental_date` = 14,665 of 51,061 (29%); payment after return_date = 1,017.
- **Options:** (a) keep and use payment_date as stated (recommended: the rule says payment month); (b) use rental_date month for revenue; (c) flag as DQ.

## 11. Paying customer differs from renting customer / staff
- **Question:** For lifetime value, is the customer the payment's customer_id or the rental's customer_id?
- **Why it matters:** payments and rentals counts per customer come from different keys.
- **Evidence:** payment.customer_id <> rental.customer_id: 5 rows. staff differs on 8,080 (affects item 1 only if staff route chosen).
- **Options:** (a) each table's own customer_id (recommended); (b) rental's customer for both.

## 12. Months and stores with no payments
- **Question:** Should the revenue mart include zero rows for store-months with no payments?
- **Why it matters:** sparse vs dense output changes row count and downstream joins.
- **Evidence:** payments span 55 months, 2022-01 to 2026-07; 500 stores exist but payments reach only 2 stores, so a dense grid is 500 x 55 = 27,500 rows vs about 110 sparse.
- **Options:** (a) sparse, only store-months with payments (recommended); (b) dense for stores that have inventory (2); (c) dense for all 500.

## 13. Money precision and rounding
- **Question:** Currency, scale, and rounding of fees and totals?
- **Why it matters:** payment.amount is numeric(5,2); fees are whole dollars, but any per-day proration would not be. Snowflake NUMBER scale on SUM must not drift to float.
- **Evidence:** not measurable (no fee data exists yet). replacement_cost range 9.99-29.99, no NULLs; rental_duration 3-7.
- **Options:** (a) NUMBER(12,2), no rounding needed (recommended); (b) other.

## 14. Rental date plus duration across DST / what "days after" means
- **Question:** Is due date rental_date + N * 24 hours or N calendar days in some zone?
- **Why it matters:** only differs if a non-UTC zone is chosen (see 6); in UTC no DST shift.
- **Evidence:** not measurable under UTC; rentals with an exactly midnight UTC rental time: 1.
- **Options:** (a) N x 24h in UTC (recommended); (b) calendar days in a named zone.
