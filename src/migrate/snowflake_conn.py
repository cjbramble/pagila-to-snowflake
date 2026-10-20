"""Snowflake connections from ~/.snowflake/connections.toml, shared with the snow CLI."""

import os

import snowflake.connector
from snowflake.connector import SnowflakeConnection

DEFAULT_CONNECTION = "pagila"


def connect(connection_name: str | None = None) -> SnowflakeConnection:
    """Open a connection by name; falls back to $SNOWFLAKE_CONNECTION, then 'pagila'."""
    name = connection_name or os.environ.get("SNOWFLAKE_CONNECTION", DEFAULT_CONNECTION)
    return snowflake.connector.connect(
        connection_name=name,
        # Short-lived scripts: always log out on close instead of probing for async queries.
        enable_server_session_keep_alive_auto_detection=False,
        session_parameters={
            # The account default is America/Los_Angeles; casting loaded timestamps to
            # TIMESTAMP_TZ would stamp them with that offset instead of UTC.
            "TIMEZONE": "UTC",
            "QUERY_TAG": "pagila-migration",
        },
    )
