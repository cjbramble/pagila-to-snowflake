"""Smoke test: connect as the service user and run one query on the warehouse."""

from migrate.snowflake_conn import connect


def main() -> None:
    with connect() as conn:
        cur = conn.cursor()
        cur.execute(
            "select current_user(), current_role(), current_warehouse(), current_database()"
        )
        user, role, warehouse, database = cur.fetchone()
        print(f"user={user} role={role} warehouse={warehouse} database={database}")

        # GENERATOR needs compute, so this proves the warehouse resumes and runs.
        cur.execute("select count(*) from table(generator(rowcount => 1000))")
        print(f"warehouse query ok: {cur.fetchone()[0]} rows")


if __name__ == "__main__":
    main()
