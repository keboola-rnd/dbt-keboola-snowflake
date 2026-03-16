import re
from unittest.mock import MagicMock

import pytest

from dbt.adapters.keboola_snowflake.connections import KeboolaHandle, _generate_session_id

UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
)


@pytest.mark.parametrize(
    'call_count',
    [1, 10, 100],
    ids=['single', 'ten', 'hundred'],
)
def test_generate_session_id_is_valid_uuidv7(call_count: int) -> None:
    """Generated session IDs must be valid UUIDv7 strings."""
    for _ in range(call_count):
        session_id = _generate_session_id()
        assert UUID_PATTERN.match(session_id), f"Not a valid UUIDv7: {session_id}"


def test_generate_session_id_is_unique() -> None:
    """Each call must produce a unique session ID."""
    ids = [_generate_session_id() for _ in range(100)]
    assert len(set(ids)) == 100


def test_generate_session_id_is_time_ordered() -> None:
    """UUIDv7 timestamp portion (first 12 hex chars) must be non-decreasing."""
    ids = [_generate_session_id() for _ in range(10)]
    # Extract the 48-bit timestamp: first 8 hex + next 4 hex (before version nibble)
    # UUID format: xxxxxxxx-xxxx-7xxx-... → first two groups = ms timestamp
    timestamps = [s.replace('-', '')[:12] for s in ids]
    assert timestamps == sorted(timestamps)


def test_keboola_handle_session_id_is_uuidv7() -> None:
    """KeboolaHandle must use UUIDv7 session IDs, unique per instance."""
    mock_client = MagicMock()
    handle1 = KeboolaHandle(mock_client, 'branch1', 'ws1')
    handle2 = KeboolaHandle(mock_client, 'branch1', 'ws1')
    assert UUID_PATTERN.match(handle1.session_id)
    assert handle1.session_id != handle2.session_id
