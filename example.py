import asyncio
import json
import logging

from aio_insight.aio_insight import AsyncInsight
from creds import jira_test_sise_token, jira_test_sise_url

# Configure logging
logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def use_aio_insight():

        session = AsyncInsight(
            url=jira_test_sise_url,
            token=jira_test_sise_token,
            verify_ssl=False
        )

        schemas = await session.get_object_schemas()
        print(json.dumps(schemas, indent=2))
        # get_object_schema = await session.get_object_schema(8)
        # print(json.dumps(get_object_schema, indent=2))

        # get_object_schema_object_types = await session.get_object_schema_object_types(8)
        # print(json.dumps(get_object_schema_object_types, indent=2))

        # get_object_schema_object_types_flat = await session.get_object_schema_object_types_flat(8)
        # print(json.dumps(get_object_schema_object_types_flat, indent=2).replace("internal-jira.test.rmv", "example.com"))

        # get_object_schema_object_attributes = await session.get_object_schema_object_attributes(8)
        # print(json.dumps(get_object_schema_object_attributes, indent=2).replace("internal-jira.test.rmv", "example.com"))


        aql_query = 'objectType = "Physical Host"'



        # Execute the AQL query
        results = await session.aql_query(
            ql_query=aql_query,
            page=1,
            result_per_page=10,
            include_attributes=True,
            include_attributes_deep=2,
            include_type_attributes=True,
            include_extended_info=True,
            # object_schema_id="8"  # Replace with your actual schema ID if needed
        )

        for result, value in results.items():
            print(result, value)


if __name__ == "__main__":
    asyncio.run(use_aio_insight())