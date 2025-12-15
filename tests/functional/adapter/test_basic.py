"""
Basic adapter tests for dbt-keboola-snowflake adapter.

These tests verify that the adapter implements core dbt functionality correctly.
"""
import pytest

from dbt.tests.adapter.basic.test_base import BaseSimpleMaterializations
from dbt.tests.adapter.basic.test_singular_tests import BaseSingularTests
from dbt.tests.adapter.basic.test_singular_tests_ephemeral import BaseSingularTestsEphemeral
from dbt.tests.adapter.basic.test_empty import BaseEmpty
from dbt.tests.adapter.basic.test_ephemeral import BaseEphemeral
from dbt.tests.adapter.basic.test_incremental import BaseIncremental
from dbt.tests.adapter.basic.test_generic_tests import BaseGenericTests
from dbt.tests.adapter.basic.test_snapshot_check_cols import BaseSnapshotCheckCols
from dbt.tests.adapter.basic.test_snapshot_timestamp import BaseSnapshotTimestamp
from dbt.tests.adapter.basic.test_adapter_methods import BaseAdapterMethod


class TestSimpleMaterializationsKeboolaSnowflake(BaseSimpleMaterializations):
    """Test basic materializations: table, view, and seed"""
    pass


class TestSingularTestsKeboolaSnowflake(BaseSingularTests):
    """Test singular (data) tests"""
    pass


class TestSingularTestsEphemeralKeboolaSnowflake(BaseSingularTestsEphemeral):
    """Test singular tests with ephemeral models"""
    pass


class TestEmptyKeboolaSnowflake(BaseEmpty):
    """Test handling of empty models"""
    pass


class TestEphemeralKeboolaSnowflake(BaseEphemeral):
    """Test ephemeral materializations"""
    pass


class TestIncrementalKeboolaSnowflake(BaseIncremental):
    """Test incremental materializations"""
    pass


class TestGenericTestsKeboolaSnowflake(BaseGenericTests):
    """Test generic (schema) tests"""
    pass


class TestSnapshotCheckColsKeboolaSnowflake(BaseSnapshotCheckCols):
    """Test snapshot functionality with check columns strategy"""
    pass


class TestSnapshotTimestampKeboolaSnowflake(BaseSnapshotTimestamp):
    """Test snapshot functionality with timestamp strategy"""
    pass


class TestBaseAdapterMethodKeboolaSnowflake(BaseAdapterMethod):
    """Test adapter-specific methods"""
    pass
