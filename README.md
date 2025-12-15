# dbt-keboola-snowflake

dbt adapter for Snowflake via Keboola Query Service.

This adapter allows you to use dbt with Snowflake databases through Keboola's Query Service API, instead of connecting directly to Snowflake.

## Installation

Install directly from GitHub:

```bash
pip install git+https://github.com/keboola-rnd/dbt-keboola-snowflake.git
```

Or install a specific version:

```bash
pip install git+https://github.com/keboola-rnd/dbt-keboola-snowflake.git@v0.2.5
```

For development, clone and install in editable mode:

```bash
git clone https://github.com/keboola-rnd/dbt-keboola-snowflake.git
cd dbt-keboola-snowflake
pip install -e .
```

## Configuration

Configure your `profiles.yml`:

```yaml
my_project:
  target: dev
  outputs:
    dev:
      type: keboola_snowflake
      base_url: https://query.keboola.com
      token: "{{ env_var('KEBOOLA_TOKEN') }}"
      branch_id: "your-branch-id"
      workspace_id: "your-workspace-id"
      database: my_database
      schema: my_schema
      warehouse: my_warehouse  # optional
```

## Required Credentials

- `base_url`: Keboola Query Service URL (e.g., `https://query.keboola.com`)
- `token`: Keboola Storage API token
- `branch_id`: Keboola branch ID
- `workspace_id`: Keboola workspace ID
- `database`: Snowflake database name
- `schema`: Snowflake schema name

## Optional Settings

- `warehouse`: Snowflake warehouse name
- `role`: Snowflake role
- `query_tag`: Query tag for tracking

## Features

This adapter supports all standard dbt features for Snowflake:

- Tables and views
- Incremental models (append, merge, delete+insert, microbatch, insert_overwrite)
- Dynamic tables
- Seeds and tests
- Snapshots

## How It Works

Instead of connecting directly to Snowflake, this adapter sends SQL queries through Keboola's Query Service API. The Query Service executes the SQL in your Keboola-managed Snowflake workspace.
