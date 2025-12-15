import pytest
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from test.env
env_file = Path(__file__).parent.parent / "test.env"
if env_file.exists():
    load_dotenv(env_file)
else:
    print(f"Warning: test.env file not found at {env_file}")

# Import the standard functional fixtures as a plugin
# Note: fixtures with session scope need to be local
pytest_plugins = ["dbt.tests.fixtures.project"]


# Override unique_schema to use the workspace schema instead of creating new schemas
# This is necessary because Keboola workspaces cannot create schemas
@pytest.fixture(scope="class")
def unique_schema(request, prefix):
    """
    Override to use fixed workspace schema instead of creating unique test schemas.
    Keboola Query Service workspaces cannot create new schemas.
    """
    return os.getenv('KEBOOLA_SCHEMA', 'WORKSPACE_1282429287')


# The profile dictionary, used to write out profiles.yml
# dbt will supply a unique schema per test, so we do not specify 'schema' here
@pytest.fixture(scope="class")
def dbt_profile_target():
    # Debug: print environment variables
    print(f"\nLoading profile with:")
    print(f"  KEBOOLA_BASE_URL: {os.getenv('KEBOOLA_BASE_URL')}")
    print(f"  KEBOOLA_TOKEN: {'***' if os.getenv('KEBOOLA_TOKEN') else None}")
    print(f"  KEBOOLA_BRANCH_ID: {os.getenv('KEBOOLA_BRANCH_ID')}")
    print(f"  KEBOOLA_WORKSPACE_ID: {os.getenv('KEBOOLA_WORKSPACE_ID')}")
    print(f"  KEBOOLA_DATABASE: {os.getenv('KEBOOLA_DATABASE', 'TEST_DATABASE')}")
    print(f"  KEBOOLA_SCHEMA: {os.getenv('KEBOOLA_SCHEMA')}")

    return {
        'type': 'keboola_snowflake',
        'threads': 1,
        'base_url': os.getenv('KEBOOLA_BASE_URL'),
        'token': os.getenv('KEBOOLA_TOKEN'),
        'branch_id': os.getenv('KEBOOLA_BRANCH_ID'),
        'workspace_id': os.getenv('KEBOOLA_WORKSPACE_ID'),
        'database': os.getenv('KEBOOLA_DATABASE', 'TEST_DATABASE'),
        # Use the workspace schema - Keboola workspaces cannot create new schemas
        'schema': os.getenv('KEBOOLA_SCHEMA', 'WORKSPACE_1282429287'),
    }
