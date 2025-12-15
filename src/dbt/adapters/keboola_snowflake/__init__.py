from dbt.adapters.keboola_snowflake.column import SnowflakeColumn
from dbt.adapters.keboola_snowflake.connections import KeboolaConnectionManager
from dbt.adapters.keboola_snowflake.connections import KeboolaSnowflakeCredentials
from dbt.adapters.keboola_snowflake.relation import SnowflakeRelation
from dbt.adapters.keboola_snowflake.impl import KeboolaSnowflakeAdapter

from dbt.adapters.base import AdapterPlugin
from dbt.include import keboola_snowflake

Plugin = AdapterPlugin(
    adapter=KeboolaSnowflakeAdapter,
    credentials=KeboolaSnowflakeCredentials,
    include_path=keboola_snowflake.PACKAGE_PATH,
)
