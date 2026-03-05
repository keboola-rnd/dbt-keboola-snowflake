import datetime
import re
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional, Tuple, Any, List, Iterable, TYPE_CHECKING, Dict
from decimal import Decimal, InvalidOperation

import pytz
import agate

from dbt_common.exceptions import (
    DbtRuntimeError,
)
from dbt_common.exceptions import DbtDatabaseError
from dbt.adapters.contracts.connection import AdapterResponse, Connection, Credentials
from dbt.adapters.sql import SQLConnectionManager
from dbt.adapters.events.logging import AdapterLogger
from dbt_common.ui import line_wrap_message, warning_tag

from keboola_query_service import Client, JobState, QueryServiceError, JobError

if TYPE_CHECKING:
    pass


logger = AdapterLogger("KeboolaSnowflake")


ERROR_REDACTION_PATTERNS = {
    re.compile(r"Row Values: \[(.|\n)*\]"): "Row Values: [redacted]",
    re.compile(r"Duplicate field key '(.|\n)*'"): "Duplicate field key '[redacted]'",
}


def _convert_value_to_python_type(value: Any, column_type: str) -> Any:
    """
    Convert string values from Keboola Query Service API to proper Python types.

    The Query Service API returns all values as strings, but we need to match
    the behavior of snowflake-connector-python which returns typed values.

    Args:
        value: The value to convert (may be string or None)
        column_type: Snowflake column type name (e.g., 'NUMBER', 'VARCHAR', 'BOOLEAN')

    Returns:
        Value converted to appropriate Python type
    """
    # Handle None/NULL values
    if value is None or value == '':
        return None

    # Normalize type name to uppercase for comparison
    column_type_upper = column_type.upper()

    # Integer types
    if column_type_upper in ('INTEGER', 'INT', 'BIGINT', 'SMALLINT', 'TINYINT', 'BYTEINT'):
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.debug(f"Failed to convert '{value}' to int for type {column_type}")
            return value

    # Float/Decimal types
    if column_type_upper in ('FLOAT', 'FLOAT4', 'FLOAT8', 'DOUBLE', 'DOUBLE PRECISION', 'REAL'):
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.debug(f"Failed to convert '{value}' to float for type {column_type}")
            return value

    # NUMBER and FIXED types (Snowflake's numeric types) - convert to Decimal or int
    # FIXED is used for exact numeric types like COUNT(*) results
    if column_type_upper.startswith('NUMBER') or column_type_upper == 'FIXED':
        try:
            # Try to parse as int first if no decimal point
            if isinstance(value, str) and '.' not in value and 'e' not in value.lower():
                return int(value)
            # Otherwise use Decimal for precision
            return Decimal(value)
        except (ValueError, TypeError, InvalidOperation):
            logger.debug(f"Failed to convert '{value}' to number for type {column_type}")
            return value

    # Decimal types
    if column_type_upper.startswith('DECIMAL') or column_type_upper.startswith('NUMERIC'):
        try:
            return Decimal(value)
        except (ValueError, TypeError, InvalidOperation):
            logger.debug(f"Failed to convert '{value}' to Decimal for type {column_type}")
            return value

    # Boolean type
    if column_type_upper == 'BOOLEAN':
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ('true', '1', 't', 'yes', 'y'):
                return True
            elif value_lower in ('false', '0', 'f', 'no', 'n'):
                return False
        logger.debug(f"Failed to convert '{value}' to bool for type {column_type}")
        return value

    # Date/Time types - for now keep as string, could parse to datetime objects if needed
    # Snowflake date/time types: DATE, TIME, TIMESTAMP, TIMESTAMP_LTZ, TIMESTAMP_NTZ, TIMESTAMP_TZ
    # The current adapter doesn't parse these, and dbt generally handles them as strings

    # String types - return as-is
    # VARCHAR, CHAR, TEXT, STRING, BINARY, VARBINARY, VARIANT, OBJECT, ARRAY

    # Default: return value unchanged (typically already a string)
    return value


_COMMENT_OR_STRING_RE = re.compile(r"'(?:[^']|'')*'|--[^\n]*")


def _strip_line_comments(sql: str) -> str:
    """Remove SQL line comments (-- ...) while preserving string literals.

    The regex matches string literals first, so '--' inside quotes is never
    treated as a comment.
    """
    return _COMMENT_OR_STRING_RE.sub(lambda m: m.group() if m.group().startswith("'") else "", sql)


class KeboolaHandle:
    """Wrapper around Keboola Client that mimics a database connection handle."""

    def __init__(
        self,
        client: Client,
        branch_id: str,
        workspace_id: str,
        database: Optional[str] = None,
        schema: Optional[str] = None,
    ):
        self.client = client
        self.branch_id = branch_id
        self.workspace_id = workspace_id
        self.database = database
        self.schema = schema
        self._session_id = f"keboola_{branch_id}_{workspace_id}"

    @property
    def session_id(self) -> str:
        return self._session_id

    def cursor(self) -> "KeboolaCursor":
        return KeboolaCursor(self)

    def close(self):
        """Close the client connection."""
        self.client.close()


class KeboolaCursor:
    """Cursor-like object for Keboola Query Service results."""

    def __init__(self, handle: KeboolaHandle):
        self.handle = handle
        self._results: Optional[List[Any]] = None
        self._columns: Optional[List[Any]] = None
        self._rowcount: int = -1
        self._description: Optional[List[Tuple]] = None
        self._sfqid: Optional[str] = None  # Query ID for compatibility
        self._sqlstate: Optional[str] = None
        self._rows: List[tuple] = []
        self._row_index: int = 0

    @property
    def rowcount(self) -> int:
        return self._rowcount

    @property
    def sfqid(self) -> Optional[str]:
        return self._sfqid

    @property
    def sqlstate(self) -> Optional[str]:
        return self._sqlstate

    @property
    def description(self) -> Optional[List[Tuple]]:
        return self._description

    def execute(self, sql: str, bindings: Optional[Any] = None) -> "KeboolaCursor":
        """Execute SQL via Keboola Query Service."""
        client = self.handle.client

        # Handle bindings by simple string substitution if needed
        if bindings:
            # Simple parameter substitution - Keboola doesn't support parameterized queries
            # Convert Python values to SQL literals
            for binding in bindings:
                if binding is None:
                    sql_value = "NULL"
                elif isinstance(binding, str):
                    # Escape single quotes and wrap in quotes
                    sql_value = "'" + binding.replace("'", "''") + "'"
                elif isinstance(binding, (int, float)):
                    sql_value = str(binding)
                elif isinstance(binding, bool):
                    sql_value = "TRUE" if binding else "FALSE"
                else:
                    # For other types (Decimal, datetime, etc.), convert to string
                    sql_value = "'" + str(binding).replace("'", "''") + "'"

                sql = sql.replace("?", sql_value, 1)

        sql = _strip_line_comments(sql)

        try:
            results = client.execute_query(
                branch_id=self.handle.branch_id,
                workspace_id=self.handle.workspace_id,
                statements=[sql],
            )

            if results and len(results) > 0:
                result = results[0]
                self._sfqid = getattr(result, "query_id", None)
                self._sqlstate = "SUCCESS" if result.status.value == "COMPLETED" else result.status.value

                # Build description from columns
                if result.columns:
                    self._description = [
                        (col.name, col.type, None, None, None, None, col.nullable)
                        for col in result.columns
                    ]

                # Store row data - convert string values to proper Python types
                if result.data and result.columns:
                    # Convert each value based on its column type
                    self._rows = []
                    for row in result.data:
                        converted_row = tuple(
                            _convert_value_to_python_type(value, col.type)
                            for value, col in zip(row, result.columns)
                        )
                        self._rows.append(converted_row)
                elif result.data:
                    # No column metadata - keep as strings
                    self._rows = [tuple(row) for row in result.data]
                else:
                    self._rows = []
                # Ensure rowcount is integer (Query Service may return string)
                rows_affected = result.rows_affected if result.rows_affected else len(self._rows)
                self._rowcount = int(rows_affected) if isinstance(rows_affected, str) else rows_affected
                self._row_index = 0
            else:
                self._rows = []
                self._rowcount = 0
                self._sqlstate = "SUCCESS"

        except JobError as e:
            self._sqlstate = "ERROR"
            error_msg = e.message if hasattr(e, "message") else str(e)
            raise KeboolaProgrammingError(error_msg, sfqid=getattr(e, "job_id", None))
        except QueryServiceError as e:
            self._sqlstate = "ERROR"
            raise KeboolaProgrammingError(str(e))

        return self

    def fetchone(self) -> Optional[tuple]:
        """Fetch the next row."""
        if self._row_index < len(self._rows):
            row = self._rows[self._row_index]
            self._row_index += 1
            return row
        return None

    def fetchmany(self, size: int = 1) -> List[tuple]:
        """Fetch multiple rows."""
        rows = self._rows[self._row_index : self._row_index + size]
        self._row_index += len(rows)
        return rows

    def fetchall(self) -> List[tuple]:
        """Fetch all remaining rows."""
        rows = self._rows[self._row_index :]
        self._row_index = len(self._rows)
        return rows

    def close(self):
        """Close the cursor."""
        self._rows = []
        self._row_index = 0


class KeboolaProgrammingError(Exception):
    """Exception raised for Keboola query errors."""

    def __init__(self, message: str, sfqid: Optional[str] = None):
        super().__init__(message)
        self.sfqid = sfqid


@dataclass
class KeboolaSnowflakeCredentials(Credentials):
    """Credentials for Keboola Query Service connection."""

    # Keboola-specific credentials
    base_url: str = ""
    token: str = ""
    branch_id: str = ""
    workspace_id: str = ""

    # Optional Snowflake-compatible settings
    warehouse: Optional[str] = None
    role: Optional[str] = None
    query_tag: Optional[str] = None

    # Connection settings
    connect_retries: int = 1
    connect_timeout: Optional[int] = None
    retry_on_database_errors: bool = False

    def __post_init__(self):
        if not self.base_url:
            raise ValueError("base_url is required for Keboola Query Service")
        if not self.token:
            raise ValueError("token is required for Keboola Query Service")
        if not self.branch_id:
            raise ValueError("branch_id is required for Keboola Query Service")
        if not self.workspace_id:
            raise ValueError("workspace_id is required for Keboola Query Service")

    @property
    def type(self):
        return "keboola_snowflake"

    @property
    def unique_field(self):
        return f"{self.base_url}_{self.workspace_id}"

    def _connection_keys(self):
        return (
            "base_url",
            "branch_id",
            "workspace_id",
            "database",
            "schema",
            "warehouse",
            "role",
            "query_tag",
            "connect_retries",
            "connect_timeout",
        )


class KeboolaConnectionManager(SQLConnectionManager):
    TYPE = "keboola_snowflake"

    @contextmanager
    def exception_handler(self, sql):
        try:
            yield
        except KeboolaProgrammingError as e:
            msg = str(e)

            # Redact sensitive data patterns
            for regex_pattern, replacement_message in ERROR_REDACTION_PATTERNS.items():
                msg = re.sub(regex_pattern, replacement_message, msg)

            logger.debug("Keboola query id: {}".format(e.sfqid))
            logger.debug("Keboola error: {}".format(msg))

            if "Empty SQL statement" in msg:
                logger.debug("got empty sql statement, moving on")
            else:
                raise DbtDatabaseError(msg)
        except Exception as e:
            logger.debug("Error running SQL: {}", sql)
            logger.debug("Rolling back transaction.")
            self.rollback_if_open()
            if isinstance(e, DbtRuntimeError):
                raise
            raise DbtRuntimeError(str(e)) from e

    @classmethod
    def open(cls, connection):
        if connection.state == "open":
            logger.debug("Connection is already open, skipping open.")
            return connection

        creds = connection.credentials

        def connect():
            client = Client(
                base_url=creds.base_url,
                token=creds.token,
            )

            handle = KeboolaHandle(
                client=client,
                branch_id=creds.branch_id,
                workspace_id=creds.workspace_id,
                database=creds.database,
                schema=creds.schema,
            )

            return handle

        retryable_exceptions = [QueryServiceError]

        return cls.retry_connection(
            connection,
            connect=connect,
            logger=logger,
            retry_limit=creds.connect_retries,
            retry_timeout=creds.connect_timeout if creds.connect_timeout is not None else lambda x: x * x,
            retryable_exceptions=retryable_exceptions,
        )

    def cancel(self, connection):
        """Cancel is not directly supported by Keboola Query Service in the same way."""
        logger.debug("Cancel requested for connection '{}'".format(connection.name))
        # Keboola jobs can be cancelled via client.cancel_job() if we track job IDs
        # For now, log a warning
        logger.warning("Query cancellation not fully implemented for Keboola Query Service")

    @classmethod
    def get_response(cls, cursor) -> AdapterResponse:
        code = cursor.sqlstate

        if code is None:
            code = "SUCCESS"

        # Ensure rowcount is an integer (Query Service may return string)
        rowcount = cursor.rowcount
        if isinstance(rowcount, str):
            rowcount = int(rowcount) if rowcount.isdigit() else 0

        query_id = str(cursor.sfqid) if cursor.sfqid is not None else None
        return AdapterResponse(
            _message="{} {}".format(code, rowcount),
            rows_affected=rowcount,
            code=code,
            query_id=query_id,
        )

    # Disable transactional logic by default (same as Snowflake)
    def add_begin_query(self, *args, **kwargs):
        pass

    def add_commit_query(self, *args, **kwargs):
        pass

    def begin(self):
        pass

    def commit(self):
        pass

    def clear_transaction(self):
        pass

    @classmethod
    def _split_queries(cls, sql):
        """Split SQL statements at semicolons into discrete queries."""
        sql_s = str(sql)
        # Simple semicolon split - handles most cases
        # More sophisticated parsing may be needed for complex SQL with strings containing semicolons
        queries = []
        current_query = []
        in_string = False
        string_char = None

        for char in sql_s:
            if char in ("'", '"') and not in_string:
                in_string = True
                string_char = char
            elif char == string_char and in_string:
                in_string = False
                string_char = None

            if char == ";" and not in_string:
                query = "".join(current_query).strip()
                if query:
                    queries.append(query)
                current_query = []
            else:
                current_query.append(char)

        # Don't forget the last query if it doesn't end with semicolon
        last_query = "".join(current_query).strip()
        if last_query:
            queries.append(last_query)

        return queries

    @staticmethod
    def _fix_rows(rows: Iterable[Iterable]) -> Iterable[Iterable]:
        """Fix datetime timezone handling for pickling compatibility."""
        for row in rows:
            fixed_row = []
            for col in row:
                if isinstance(col, datetime.datetime) and col.tzinfo:
                    offset = col.utcoffset()
                    assert offset is not None
                    offset_seconds = offset.total_seconds()
                    new_timezone = pytz.FixedOffset(int(offset_seconds // 60))
                    col = col.astimezone(tz=new_timezone)
                fixed_row.append(col)

            yield fixed_row

    @classmethod
    def process_results(cls, column_names, rows):
        return super().process_results(column_names, cls._fix_rows(rows))

    def execute(
        self, sql: str, auto_begin: bool = False, fetch: bool = False, limit: Optional[int] = None
    ) -> Tuple[AdapterResponse, "agate.Table"]:
        from dbt_common.clients.agate_helper import empty_table

        _, cursor = self.add_query(sql, auto_begin)
        response = self.get_response(cursor)
        if fetch:
            table = self.get_result_from_cursor(cursor, limit)
        else:
            table = empty_table()
        return response, table

    def add_standard_query(self, sql: str, **kwargs) -> Tuple[Connection, Any]:
        return super().add_query(self._add_query_comment(sql), **kwargs)

    def add_query(
        self,
        sql: str,
        auto_begin: bool = True,
        bindings: Optional[Any] = None,
        abridge_sql_log: bool = False,
        *args,
        **kwargs,
    ) -> Tuple[Connection, Any]:
        if bindings:
            bindings = tuple(bindings)

        stripped_queries = self._stripped_queries(sql)

        if set(query.lower() for query in stripped_queries).issubset({"begin;", "commit;"}):
            connection, cursor = self._add_begin_commit_only_queries(
                stripped_queries,
                auto_begin=auto_begin,
                bindings=bindings,
                abridge_sql_log=abridge_sql_log,
            )
        else:
            connection, cursor = self._add_standard_queries(
                stripped_queries,
                auto_begin=auto_begin,
                bindings=bindings,
                abridge_sql_log=abridge_sql_log,
            )

        if cursor is None:
            self._raise_cursor_not_found_error(sql)

        return connection, cursor

    def _stripped_queries(self, sql: str) -> List[str]:
        def strip_query(query):
            without_comments_re = re.compile(
                r"(\".*?\"|\'.*?\')|(/\*.*?\*/|--[^\r\n]*$)", re.MULTILINE
            )
            return re.sub(without_comments_re, "", query).strip()

        return [query for query in self._split_queries(sql) if strip_query(query) != ""]

    def _add_begin_commit_only_queries(
        self, queries: List[str], **kwargs
    ) -> Tuple[Connection, Any]:
        message = (
            "Explicit transactional logic should be used only to wrap "
            "DML logic (MERGE, DELETE, UPDATE, etc). The keywords BEGIN; and COMMIT; should "
            "be placed directly before and after your DML statement, rather than in separate "
            "statement calls or run_query() macros."
        )
        logger.warning(line_wrap_message(warning_tag(message)))

        for query in queries:
            connection, cursor = self.add_standard_query(query, **kwargs)
        return connection, cursor

    def _add_standard_queries(self, queries: List[str], **kwargs) -> Tuple[Connection, Any]:
        for query in queries:
            if query.lower() == "begin;":
                super().add_begin_query()
            elif query.lower() == "commit;":
                super().add_commit_query()
            else:
                connection, cursor = self.add_standard_query(query, **kwargs)
        return connection, cursor

    def _raise_cursor_not_found_error(self, sql: str):
        conn = self.get_thread_connection()
        try:
            conn_name = conn.name
        except AttributeError:
            conn_name = None

        raise DbtRuntimeError(
            f"""Tried to run an empty query on model '{conn_name or "<None>"}'. If you are """
            f"""conditionally running\nsql, e.g. in a model hook, make """
            f"""sure your `else` clause contains valid sql!\n\n"""
            f"""Provided SQL:\n{sql}"""
        )

    @classmethod
    def data_type_code_to_name(cls, type_code) -> str:
        """Convert type code to name - Keboola returns type names directly."""
        if isinstance(type_code, str):
            return type_code
        # Fallback for numeric codes
        return str(type_code)
