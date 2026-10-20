"""Named faults that corrupt one RAW table the way real migrations go wrong."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Fault:
    name: str
    table: str
    description: str
    statements: tuple[str, ...]  # {t} is replaced with the fully qualified RAW table


FAULTS = {
    f.name: f
    for f in [
        Fault(
            "drop_rows",
            "payment",
            "3 payments silently not loaded",
            (
                "DELETE FROM {t} WHERE PAYMENT_ID IN"
                " (SELECT PAYMENT_ID FROM {t} ORDER BY PAYMENT_ID LIMIT 3)",
            ),
        ),
        Fault(
            "truncate_strings",
            "film",
            "description cut to 100 characters, as by a too-narrow VARCHAR",
            (
                "UPDATE {t} SET DESCRIPTION = LEFT(DESCRIPTION, 100)"
                " WHERE LENGTH(DESCRIPTION) > 100",
            ),
        ),
        Fault(
            "shift_timestamps_tz",
            "rental",
            "rental_date read as America/Los_Angeles wall-clock instead of UTC (+7h)",
            ("UPDATE {t} SET RENTAL_DATE = DATEADD(HOUR, 7, RENTAL_DATE)",),
        ),
        Fault(
            "perturb_decimal",
            "payment",
            "one payment amount off by a cent",
            ("UPDATE {t} SET AMOUNT = AMOUNT + 0.01 WHERE PAYMENT_ID = 16050",),
        ),
        Fault(
            "null_out_column",
            "customer",
            "email lost for 5 customers",
            ("UPDATE {t} SET EMAIL = NULL WHERE CUSTOMER_ID <= 5",),
        ),
        Fault(
            "duplicate_rows",
            "rental",
            "2 rentals loaded twice, as by a retried batch",
            (
                "INSERT INTO {t} SELECT * FROM {t} WHERE RENTAL_ID IN"
                " (SELECT RENTAL_ID FROM {t} ORDER BY RENTAL_ID LIMIT 2)",
            ),
        ),
        Fault(
            "swap_fk_values",
            "rental",
            "customer_id swapped between two rentals",
            (
                """UPDATE {t} t SET CUSTOMER_ID = s.SWAPPED
                FROM (
                    WITH pair AS (
                        SELECT RENTAL_ID, CUSTOMER_ID FROM {t}
                        WHERE RENTAL_ID IN (SELECT MIN(RENTAL_ID) FROM {t})
                           OR RENTAL_ID = (SELECT MIN(RENTAL_ID) FROM {t} WHERE CUSTOMER_ID <>
                                (SELECT CUSTOMER_ID FROM {t} ORDER BY RENTAL_ID LIMIT 1))
                    )
                    SELECT p.RENTAL_ID, q.CUSTOMER_ID AS SWAPPED
                    FROM pair p JOIN pair q ON p.RENTAL_ID <> q.RENTAL_ID
                ) s
                WHERE t.RENTAL_ID = s.RENTAL_ID""",
            ),
        ),
        Fault(
            "orphan_fk",
            "payment",
            "one payment points at a rental that doesn't exist",
            ("UPDATE {t} SET RENTAL_ID = 99999999 WHERE PAYMENT_ID = 16050",),
        ),
        Fault(
            "trailing_whitespace",
            "film",
            "one title gains a trailing space",
            ("UPDATE {t} SET TITLE = TITLE || ' ' WHERE FILM_ID = 7",),
        ),
        Fault(
            "truncate_microseconds",
            "payment",
            "payment_date loses sub-millisecond precision",
            ("UPDATE {t} SET PAYMENT_DATE = DATE_TRUNC('MILLISECOND', PAYMENT_DATE)",),
        ),
        Fault(
            "drop_check_constraint",
            "film",
            "the rating CHECK constraint (decision D08) is missing from the target",
            ("ALTER TABLE {t} DROP CONSTRAINT FILM_RATING_CHK",),
        ),
        Fault(
            "tiny_vector_drift",
            "film_embedding",
            "one embedding element drifts by 1e-7",
            (
                "UPDATE {t} SET EMBEDDING = "
                "[0,0,0,0,0,0,0,0,0,1,0,0,1,0,0,1,0.2878001,0,0.55,0.75]::VECTOR(FLOAT, 20)"
                " WHERE FILM_ID = 1",
            ),
        ),
    ]
}
