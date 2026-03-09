import pytest

from dbt.adapters.keboola_snowflake.connections import _strip_line_comments


@pytest.mark.parametrize(
    ("sql", "expected"),
    [
        # Basic stripping
        ("SELECT 1 -- comment", "SELECT 1 "),
        # Full-line comment followed by real SQL
        ("-- comment\nSELECT 1", "\nSELECT 1"),
        # No comments — idempotent
        ("SELECT 1", "SELECT 1"),
        # Empty string
        ("", ""),
        # Single-quoted string containing --
        ("SELECT 'hello -- world'", "SELECT 'hello -- world'"),
        # Escaped single quotes inside string
        ("SELECT 'it''s -- fine'", "SELECT 'it''s -- fine'"),
        # Double-quoted identifier containing --
        ('SELECT "MY--COL" FROM t', 'SELECT "MY--COL" FROM t'),
        # Escaped double quotes inside identifier
        ('SELECT "col""--name"', 'SELECT "col""--name"'),
        # Block comment containing --
        ("SELECT /* this -- x */ 1", "SELECT /* this -- x */ 1"),
        # Dollar-quoted string containing --
        ("SELECT $$hello -- world$$", "SELECT $$hello -- world$$"),
        # Mixed: double-quoted id, single-quoted string, block comment, eol comment
        (
            "SELECT \"MY--COL\", 'it''s -- ok' /* blk -- cmt */ FROM t -- eol",
            "SELECT \"MY--COL\", 'it''s -- ok' /* blk -- cmt */ FROM t ",
        ),
    ],
    ids=[
        "basic_strip",
        "full_line_comment",
        "no_comments",
        "empty_string",
        "single_quoted_preserves",
        "escaped_single_quotes",
        "double_quoted_preserves",
        "escaped_double_quotes",
        "block_comment_preserves",
        "dollar_quoted_preserves",
        "mixed",
    ],
)
def test_strip_line_comments(sql: str, expected: str) -> None:
    assert _strip_line_comments(sql) == expected
