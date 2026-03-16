import pytest
from unittest.mock import MagicMock

from dbt.adapters.keboola_snowflake.connections import KeboolaHandle


def test_cursor_execute_passes_session_id() -> None:
    """KeboolaCursor.execute() must pass the handle's session_id to execute_query."""
    mock_client = MagicMock()
    mock_client.execute_query.return_value = []
    handle = KeboolaHandle(mock_client, 'branch1', 'ws1')
    cursor = handle.cursor()

    cursor.execute("SELECT 1")

    mock_client.execute_query.assert_called_once()
    call_kwargs = mock_client.execute_query.call_args
    assert call_kwargs.kwargs.get('session_id') == handle.session_id
