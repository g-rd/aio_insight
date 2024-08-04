# AsyncQueryInsight

## Overview

`AsyncQueryInsight` is a Python library designed to interact with Jira Insight's API asynchronously. 
This library leverages Python's `asyncio` and `httpx` to efficiently query and retrieve data from Jira Insight, 
supporting asynchronous fetching of paginated data, schema processing, and concurrent request management.
It is ideal for applications that require high-performance data access and manipulation from Jira Insight.


This project is based on the [Atlassian Python API](https://github.com/atlassian-api/atlassian-python-api), 
with methods rewritten to support asynchronous operations, providing improved performance and scalability.

## Features

- **Asynchronous Data Fetching:** Utilizes Python's `asyncio` and `httpx` for concurrent HTTP requests, ensuring high throughput and minimal latency.
- **Comprehensive API Interaction:** Provides methods for executing IQL (Insight Query Language) queries, retrieving object schemas, and handling complex data models.
- **Error Handling:** Includes custom exceptions for robust error reporting and handling.
- **Configurable Parameters:** Allows customization of settings like page size, schema ID, and concurrent request limits.
- **Schema Processing:** Automatically processes schemas for object attributes, supporting detailed data models in Insight.

## Installation

Ensure you have Python 3.7+ installed. You can install the required dependencies via pip:

```bash
pip install httpx
```

## Usage

Below are examples of how to use the `AsyncQueryInsight` class and its methods.

### Using `AsyncQueryInsight`

The `AsyncQueryInsight` class is the primary interface for querying Jira Insight data asynchronously. Here's an example of how to set it up and fetch data:

```python
import asyncio
from aio_insight.aio_query_insight import AsyncQueryInsight, PageFetchError


async def main():
    # Initialize AsyncQueryInsight with necessary parameters
    query_insight = AsyncQueryInsight(
        url="https://your-jira-instance.atlassian.net",
        token="your-api-token",
        query="objectType = 'Hardware'",  # Example IQL query
        schema_id=1234,  # Optional, specify your schema ID
        page_size=50  # Optional, defaults to 20
    )

    try:
        # Fetch data pages asynchronously
        pages = await query_insight.fetch_pages()
        for page in pages:
            print(page)
    except PageFetchError as e:
        print(f"Error fetching pages: {e.message}")


# Run the async main function
asyncio.run(main())
```

### Using `get_object_by_aql`

In addition to querying data using `fetch_pages`, you can retrieve specific objects using AQL (Asset Query Language) with the `get_object_by_aql` method:

```python
import asyncio
from aio_insight import AsyncInsight

async def get_object():
    # Initialize the AsyncInsight client
    insight_client = AsyncInsight(
        url="https://your-jira-instance.atlassian.net",
        token="your-api-token"
    )

    try:
        # Define your AQL query
        aql_query = "Name = 'Laptop' AND Status = 'In Use'"
        schema_id = 1234  # Specify your schema ID

        # Fetch the object using AQL
        result = await insight_client.iql(
            query=aql_query,
            object_schema_id=schema_id
        )

        print("Objects found:")
        for obj in result.get("objects", []):
            print(obj)

    except Exception as e:
        print(f"Error retrieving objects: {e}")

# Run the async function
asyncio.run(get_object())
```

### Initialization Parameters

- **url** (str): The base URL for the Jira instance.
- **token** (str): The authentication token for accessing Jira.
- **query** (str|None): The IQL query string to execute. Can be `None`.
- **schema_id** (int|None): The ID of the schema to query against. Defaults to `None`.
- **page_size** (int|None): The number of results to return per page. Defaults to `20`.
- **rate_limiter** (RateLimiter|None): An optional rate limiter instance for managing API rate limits.

### Methods

- **fetch_pages()**: Fetches multiple pages of data asynchronously and returns a list of pages. 
    Each page is a dictionary containing the data for that page.
- **get_object_by_aql(query, schema_id)**: Retrieves specific objects based on an AQL query and schema ID.

### Error Handling

- **PageFetchError**: Raised when there is an issue in fetching pages from the API. Includes an informative error message.

## Configuration

You can customize the behavior of `AsyncQueryInsight` by modifying class-level attributes:

- **PAGE_SIZE**: Default number of results per page (default: `20`).
- **INCLUDE_ATTRIBUTES_DEEP**: Level of attribute depth to include (default: `2`).
- **INCLUDE_TYPE_ATTRIBUTES**: Whether to include type attributes (default: `False`).
- **CONCURRENT_REQUESTS**: Number of concurrent requests allowed (default: `20`).

## Dependencies

This project requires the following package:

- `httpx`
- `aiohttp` 
- `anyio` 
- `certifi` 
- `h11` 
- `httpcore` 
- `idna` 
- `oauthlib` 
- `six` 
- `sniffio`

## Contributing

Contributions are welcome! Please submit issues and pull requests to the
[GitHub repository](https://github.com/yourusername/async-query-insight).

## License

This project is licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

---

This library includes methods and concepts derived 
from the [Atlassian Python API](https://github.com/atlassian-api/atlassian-python-api),
which is licensed under the Apache License 2.0. 
The original project inspired the asynchronous reimplementation of its methods.

```# aio_insight
