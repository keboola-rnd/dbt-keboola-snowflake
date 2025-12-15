# Testing dbt-keboola-snowflake Adapter

This directory contains the test suite for the dbt-keboola-snowflake adapter.

## Setup

### 1. Install test dependencies

```bash
source venv/bin/activate
pip install pytest pytest-dotenv dbt-tests-adapter
```

### 2. Configure test environment

Copy the example environment file and fill in your Keboola credentials:

```bash
cp test.env.example test.env
```

Edit `test.env` with your actual Keboola connection details:

```
KEBOOLA_BASE_URL=https://connection.keboola.com
KEBOOLA_TOKEN=your-keboola-token-here
KEBOOLA_BRANCH_ID=your-branch-id
KEBOOLA_WORKSPACE_ID=your-workspace-id
KEBOOLA_DATABASE=TEST_DATABASE
```

**Note:** The `test.env` file is in `.gitignore` to prevent committing sensitive credentials.

## Running Tests

### Run all tests

```bash
python3 -m pytest tests/functional
```

### Run specific test classes

```bash
# Run only materialization tests
python3 -m pytest tests/functional/adapter/test_basic.py::TestSimpleMaterializationsKeboolaSnowflake

# Run only incremental tests
python3 -m pytest tests/functional/adapter/test_basic.py::TestIncrementalKeboolaSnowflake
```

### Run with verbose output

```bash
python3 -m pytest tests/functional -v
```

### Run with output capture disabled (to see print statements and logs)

```bash
python3 -m pytest tests/functional -s
```

## Test Structure

The tests are organized as follows:

- `tests/conftest.py` - Main configuration file that sets up the dbt profile for testing
- `tests/functional/adapter/test_basic.py` - Core adapter tests including:
  - Table, view, and seed materializations
  - Incremental models
  - Snapshots
  - Data tests (singular and generic)
  - Ephemeral models
  - Adapter-specific methods

## Test Coverage

The basic adapter tests verify:

- ✅ **Simple Materializations** - Tables, views, and seeds
- ✅ **Singular Tests** - Data quality tests
- ✅ **Ephemeral Models** - In-memory temporary models
- ✅ **Incremental Models** - Efficient updates to existing tables
- ✅ **Generic Tests** - Schema tests (unique, not_null, etc.)
- ✅ **Snapshots** - Type-2 slowly changing dimensions
- ✅ **Adapter Methods** - Database-specific operations

## Troubleshooting

### Connection Issues

If tests fail with connection errors:

1. Verify your credentials in `test.env` are correct
2. Ensure your Keboola workspace is active and accessible
3. Check that your token has the necessary permissions

### Test Failures

If specific tests fail:

1. Run with `-s` flag to see detailed output
2. Check if the feature is supported by Keboola Query Service
3. Review the adapter implementation for any limitations

### Debugging

To debug a specific test, add the `--pdb` flag:

```bash
python3 -m pytest tests/functional/adapter/test_basic.py::TestIncrementalKeboolaSnowflake --pdb
```

## Adding Custom Tests

To add adapter-specific tests:

1. Create a new test file in `tests/functional/adapter/`
2. Import fixtures from `dbt.tests.util`
3. Define your test class and methods
4. Use the standard pytest patterns

Example:

```python
import pytest
from dbt.tests.util import run_dbt

class TestCustomFeature:
    @pytest.fixture(scope="class")
    def models(self):
        return {
            "my_model.sql": "select 1 as id"
        }

    def test_custom_behavior(self, project):
        results = run_dbt(["run"])
        assert len(results) == 1
```

## Environment Variables

The following environment variables are used in tests:

- `KEBOOLA_BASE_URL` - Base URL for Keboola API (required)
- `KEBOOLA_TOKEN` - Keboola authentication token (required)
- `KEBOOLA_BRANCH_ID` - Branch ID for the workspace (required)
- `KEBOOLA_WORKSPACE_ID` - Workspace ID (required)
- `KEBOOLA_DATABASE` - Database name (optional, defaults to TEST_DATABASE)

## CI/CD Integration

To run tests in CI/CD, set the environment variables as secrets and run:

```bash
pytest tests/functional --junitxml=test-results.xml
```
