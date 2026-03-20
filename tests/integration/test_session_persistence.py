"""
Integration test: verify that the Keboola Query Service preserves the Snowflake
session (including TEMPORARY tables) across separate execute_query calls that
share the same session_id.

This test requires live QS credentials in the environment:
  KEBOOLA_BASE_URL, KEBOOLA_TOKEN, KEBOOLA_BRANCH_ID, KEBOOLA_WORKSPACE_ID

Run with:
  pytest tests/integration/test_session_persistence.py -v -m integration

Background
----------
Each KeboolaHandle generates one session_id and passes it to every execute_query
call.  The QS backend supports session_id to join an existing Snowflake session.
If sessions truly persist, TEMPORARY tables created in call 1 should be visible
in call 2 — which means the TRANSIENT workaround in snapshot.sql is unnecessary.
"""

import os
import uuid

import pytest

from keboola_query_service import Client


def _skip_without_creds() -> None:
    required = ["KEBOOLA_BASE_URL", "KEBOOLA_TOKEN", "KEBOOLA_BRANCH_ID", "KEBOOLA_WORKSPACE_ID"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        pytest.skip(f"Integration credentials missing: {', '.join(missing)}")


@pytest.mark.integration
def test_temporary_table_survives_across_calls() -> None:
    """
    TEMPORARY table created in call 1 must be queryable in call 2 with the
    same session_id, proving QS session persistence.
    """
    _skip_without_creds()

    session_id = str(uuid.uuid4())
    table_name = f"_session_test_{uuid.uuid4().hex[:8]}"

    client = Client(
        base_url=os.environ["KEBOOLA_BASE_URL"],
        token=os.environ["KEBOOLA_TOKEN"],
    )

    branch_id = os.environ["KEBOOLA_BRANCH_ID"]
    workspace_id = os.environ["KEBOOLA_WORKSPACE_ID"]

    try:
        # Call 1: create a TEMPORARY table and insert a row
        client.execute_query(
            branch_id=branch_id,
            workspace_id=workspace_id,
            statements=[
                f"CREATE TEMPORARY TABLE {table_name} (id INT)",
                f"INSERT INTO {table_name} VALUES (42)",
            ],
            transactional=False,
            session_id=session_id,
        )

        # Call 2: query the TEMPORARY table with the SAME session_id
        results = client.execute_query(
            branch_id=branch_id,
            workspace_id=workspace_id,
            statements=[f"SELECT id FROM {table_name}"],
            transactional=False,
            session_id=session_id,
        )

        assert len(results) == 1, "Expected exactly one statement result"
        rows = results[0].data
        assert rows is not None and len(rows) == 1, (
            f"Expected one row in TEMPORARY table; got {rows!r}. "
            "Session was NOT preserved — TRANSIENT workaround is still needed."
        )
        assert rows[0][0] in (42, "42"), f"Unexpected row value: {rows[0][0]!r}"

    finally:
        # Best-effort cleanup (may fail if session expired — that's fine)
        try:
            client.execute_query(
                branch_id=branch_id,
                workspace_id=workspace_id,
                statements=[f"DROP TABLE IF EXISTS {table_name}"],
                transactional=False,
                session_id=session_id,
            )
        except Exception:
            pass
        client.close()
