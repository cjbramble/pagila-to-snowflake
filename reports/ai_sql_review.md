# Review: AI-generated validation SQL

The `dq-triage` agent wrote validation SQL for three requirements from the requirement text, `mapping/type_mapping.yml`, and the live data only. It was barred from the existing implementation (`tests/`, `src/reconcile/`, `dbt/`, `sql/reconciliation/`). It ran every query with the read-only tool. All three requirements hold on the current data, and every query executed.

**Status:** findings by Claude, **confirmed by human review on 2026-10-20**. Logged as defects 19-23 in `AI_LOG.md`.

## Findings

| # | Req | Severity | Finding | Evidence |
|---|---|---|---|---|
| A | ETL-006 | Medium (latent) | The boundary diagnostics use `DATEDIFF('second', ...)`, which counts second boundaries crossed, not elapsed time. A return 1 day + 0.8 s after due gives `DATEDIFF('second') = 86400`, so the `exact_day_boundaries` check says "exact day" (true elapsed time is 86,400,800,000 µs). `one_sec_late` (`DATEDIFF('second') <= 1`) has the same flaw. The agent used microseconds correctly in its own self-consistency query, so it's inconsistent within one answer. | Literal probe: `MOD(DATEDIFF('second', '…10:00:00.1', next day '…10:00:00.9'), 86400) = 0` is **True**. On today's data the second- and microsecond-based counts agree (12 = 12), so it's latent: correct now, wrong by construction. |
| B | ETL-002 | Low | The `c1` checksum weights `payment_count` by year and month only, with no store. Moving payment counts between stores in the same month leaves `c1` unchanged. `c2` covers revenue per store but not counts. | Read the formula: `sum(pc*year*100 + pc*month)` has no `store_id` term. |
| C | ETL-002 | Medium | The acceptance criterion "store totals equal the legacy `sales_by_store` view" isn't checked. The agent said so. | The agent's own "Assumptions and risks" note. |
| D | All three | Low (design) | Comparisons are aggregate fingerprints (counts, sums, `sum(rental_id)` per bucket, weighted checksums), not row-level diffs. Offsetting errors inside a bucket pass. The agent flagged this and chose it because of the 200-row cap. | Agent's notes. The production suite does this row by row (MIG-005, and `tests/etl/` compares all 51,805 rentals). |
| E | MIG-004 | Low (process) | The reported SQL is abbreviated (`UNION ALL ...`, "the blocks for the other columns have the same shape"). The artifact can't be reviewed or reused as delivered. | The report text. |

**What it got right:**
- Its interpretations match the written rules.
- It handled UTC month bucketing (`AT TIME ZONE 'UTC'`) and microsecond timestamp formatting on both sides.
- It noticed that the 1-second and 24 h + 1 s acceptance cases don't occur in the data, and said they need synthetic rows. The dbt unit test covers them.
- It stated its own blind spots, aggregate fingerprints and the unchecked legacy view, without being asked.

## Generated SQL (as reported by the agent)

### ETL-006: Days late

```sql
-- pg: expected values from raw tables, epoch arithmetic
WITH x AS (
  SELECT r.rental_id,
    CASE WHEN r.return_date IS NULL THEN 'not_returned'
         WHEN extract(epoch FROM r.return_date) - extract(epoch FROM r.rental_date) - f.rental_duration*86400 > 0 THEN 'late'
         ELSE 'on_time' END AS st,
    extract(epoch FROM r.return_date) - extract(epoch FROM r.rental_date) - f.rental_duration*86400 AS secs
  FROM rental r JOIN inventory i USING (inventory_id) JOIN film f USING (film_id)),
y AS (SELECT rental_id, st,
       CASE st WHEN 'late' THEN ceil(secs/86400.0)::int WHEN 'on_time' THEN 0 END AS dl, secs FROM x)
SELECT st, dl, count(*) n, sum(rental_id) sum_id,
  sum(CASE WHEN st='late' AND secs::numeric % 86400 = 0 THEN 1 ELSE 0 END) exact_day_boundaries,
  sum(CASE WHEN st='late' AND secs<=1 THEN 1 ELSE 0 END) one_sec_late
FROM y GROUP BY 1,2 ORDER BY 1,2;
```

```sql
-- sf: same shape from the mart (finding A is in the last two columns)
SELECT return_status st, days_late dl, count(*) n, sum(rental_id) sum_id,
  sum(IFF(return_status='late' AND MOD(DATEDIFF('second', due_at, return_date),86400)=0,1,0)) exact_day_boundaries,
  sum(IFF(return_status='late' AND DATEDIFF('second', due_at, return_date)<=1,1,0)) one_sec_late
FROM PAGILA_MIG.MARTS.MART_RENTAL_RETURNS GROUP BY 1,2 ORDER BY 1,2;
```

```sql
-- sf: self-consistency, expect 0
SELECT count(*) bad FROM PAGILA_MIG.MARTS.MART_RENTAL_RETURNS
WHERE return_status='late' AND days_late <> CEIL(DATEDIFF('microsecond', due_at, return_date)/86400000000.0);
```

The grouped outputs were identical on both sides (9 buckets, 51,805 rows), and `bad` = 0.

### ETL-002: Monthly revenue by store

```sql
-- pg
SELECT count(*) n_rows, sum(pc) pc, sum(rev) rev,
  sum(pc*extract(year from m)*100+pc*extract(month from m)) c1,
  sum(rev*(store_id*1000+extract(year from m)*12+extract(month from m))) c2
FROM (SELECT i.store_id, date_trunc('month', p.payment_date AT TIME ZONE 'UTC')::date m,
             count(*) pc, sum(p.amount) rev
      FROM payment p JOIN rental r USING (rental_id) JOIN inventory i USING (inventory_id)
      GROUP BY 1,2) t;
```

```sql
-- sf
SELECT count(*) n_rows, sum(payment_count) pc, sum(revenue) rev,
  sum(payment_count*year(revenue_month)*100+payment_count*month(revenue_month)) c1,
  sum(revenue*(store_id*1000+year(revenue_month)*12+month(revenue_month))) c2
FROM PAGILA_MIG.MARTS.MART_MONTHLY_STORE_REVENUE;
```

Both sides returned `110 | 51061 | 170962.39 | 10332289601 | 4407998274.05`. The shape check (`day <> 1 OR payment_count <= 0`) returned 0.

### MIG-004: rental aggregates

The agent reported only the `rental_id` and `rental_date` blocks of a long-format `UNION ALL` (finding E):

```sql
-- pg
SELECT 'rental_id' c, count(*)-count(rental_id) nulls, count(DISTINCT rental_id) dist,
       min(rental_id)::text mn, max(rental_id)::text mx, sum(rental_id)::text s FROM rental
UNION ALL
SELECT 'rental_date', count(*)-count(rental_date), count(DISTINCT rental_date),
       to_char(min(rental_date) AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS.US'),
       to_char(max(rental_date) AT TIME ZONE 'UTC','YYYY-MM-DD HH24:MI:SS.US'), NULL FROM rental
UNION ALL ... ORDER BY 1;
```

```sql
-- sf (rental_date block)
SELECT 'rental_date', count(*)-count(rental_date), count(DISTINCT rental_date),
       to_char(convert_timezone('UTC',min(rental_date)),'YYYY-MM-DD HH24:MI:SS.FF6'),
       to_char(convert_timezone('UTC',max(rental_date)),'YYYY-MM-DD HH24:MI:SS.FF6'), NULL
FROM PAGILA_MIG.RAW.RENTAL ...
```

All 8 columns matched. `rental` has no free-text columns, so the collation trap I expected this requirement to probe never came up: a gap in my choice of test case, not a defect in its SQL.
