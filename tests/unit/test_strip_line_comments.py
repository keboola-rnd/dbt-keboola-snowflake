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
        # Block comment spanning multiple lines containing --
        ("SELECT 1 /* multi\nline\n-- with dash */ FROM t", "SELECT 1 /* multi\nline\n-- with dash */ FROM t"),
        # Unterminated block comment — copy through unchanged
        ("SELECT 1 /* unterminated", "SELECT 1 /* unterminated"),
        # Unterminated single-quoted string — copy through unchanged
        ("SELECT 'unterminated", "SELECT 'unterminated"),
        # Trailing line comment with no newline at end
        ("SELECT 1 -- trailing", "SELECT 1 "),
        # CRLF line endings — \r\n preserved after stripping comment
        ("SELECT 1 -- x\r\nFROM t", "SELECT 1 \r\nFROM t"),
        # Lone CR line endings (old Mac) — \r preserved after stripping comment
        ("SELECT 1 -- x\rFROM t", "SELECT 1 \rFROM t"),
        # Empty dollar-quoted string with a trailing comment
        ("SELECT $$$$ -- c", "SELECT $$$$ "),
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
        "multiline_block_comment",
        "unterminated_block_comment",
        "unterminated_single_quote",
        "trailing_line_comment_no_newline",
        "crlf_line_endings",
        "lone_cr_line_ending",
        "empty_dollar_quote",
    ],
)
def test_strip_line_comments(sql: str, expected: str) -> None:
    assert _strip_line_comments(sql) == expected
