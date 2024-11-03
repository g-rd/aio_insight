# AIOInsight - Asynchronous Jira Insight/Assets Client

## Overview

`AIOInsight` is an asynchronous Python library for interacting with Jira Insight's API. It leverages `asyncio` and `httpx` for high-performance data retrieval and management, supporting complex data models, schema processing, and concurrent requests.

This project is based on the Atlassian Python API, with methods rewritten to support asynchronous operations, providing improved performance and scalability.

## Features

- **Asynchronous Operations:** Uses `asyncio` and `httpx` for concurrent HTTP requests, ensuring high throughput.
- **Comprehensive API Interaction:** Retrieve schemas, manage objects, and handle data models.
- **Error Handling:** Includes custom exceptions for robust error handling.
- **Configurable Parameters:** Allows customization of settings for optimized performance.
- **Schema Processing:** Automates schema processing for detailed data models in Insight.

## Installation

Install dependencies:

```bash
pip install httpx aiohttp anyio
```

## Usage Example

```python
import asyncio
import logging
from aio_insight.aio_insight import AsyncInsight
from creds import assets_token, assets_url, assets_username

logging.basicConfig(level=logging.ERROR, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def use_aio_insight():
    async with AsyncInsight(
            url=assets_url,
            username=assets_username,
            password=assets_token,
            cloud=True
    ) as session:
        object_schemas = await session.get_object_schemas()
        print(object_schemas)

if __name__ == "__main__":
    asyncio.run(use_aio_insight())
```

## Supported API Endpoints

1. **`get_object_schemas()`**
   - **Description:** Retrieves all object schemas available in Jira Insight.
   - **Returns:** A list of object schemas, each including details such as schema ID, name, and object types within the schema.

2. **`get_object_schema(schema_id)`**
   - **Description:** Fetches detailed information about a specific object schema by its ID.
   - **Parameters:**
     - `schema_id` (int): The ID of the object schema.
   - **Returns:** A dictionary with information about the specified schema, including name, attributes, and associated object types.

3. **`create_object_schema(name, description)`**
   - **Description:** Creates a new object schema in Jira Insight.
   - **Parameters:**
     - `name` (str): Name for the new schema.
     - `description` (str): Description for the new schema.
   - **Returns:** A dictionary containing the created schema's details, such as schema ID, name, and description.

4. **`update_object_schema(schema_id, name, description)`**
   - **Description:** Updates an existing schema’s name and description.
   - **Parameters:**
     - `schema_id` (int): ID of the schema to update.
     - `name` (str): New name for the schema.
     - `description` (str): New description for the schema.
   - **Returns:** A dictionary with updated schema information.

5. **`get_object_schema_object_types(schema_id)`**
   - **Description:** Lists all object types within a given schema.
   - **Parameters:**
     - `schema_id` (int): ID of the object schema.
   - **Returns:** A list of object types, each including details like type ID, name, and attributes.

6. **`get_object_schema_object_types_flat(schema_id)`**
   - **Description:** Retrieves object types in a flat structure for a given schema.
   - **Parameters:**
     - `schema_id` (int): ID of the object schema.
   - **Returns:** A list of object types without hierarchical organization, including type details.

7. **`get_object_schema_object_attributes(schema_id, ...)`**
   - **Description:** Retrieves all attributes for the specified schema, with options for filtering and sorting.
   - **Parameters:** Additional filters such as `only_value_editable`, `order_by_name`, etc.
   - **Returns:** A list of attributes associated with the schema, with details like attribute ID, name, type, and editability.

8. **`get_object(object_id)`**
   - **Description:** Retrieves information about a specific object by its ID.
   - **Parameters:**
     - `object_id` (int): The ID of the object.
   - **Returns:** A dictionary with object details, including attributes, relationships, and type.

9. **`get_objects_by_aql(schema_id, object_type_id, aql_query, ...)`**
   - **Description:** Searches for objects based on an AQL (Asset Query Language) query.
   - **Parameters:**
     - `schema_id` (int): ID of the schema.
     - `object_type_id` (int): ID of the object type.
     - `aql_query` (str): The AQL query string.
   - **Returns:** A paginated dictionary of matching objects, including object attributes and type details.

10. **`get_object_type_attributes(object_type_id, ...)`**
    - **Description:** Retrieves attributes for a specific object type, with options to filter or sort results.
    - **Parameters:** Filters like `only_value_editable`, `order_by_name`, etc.
    - **Returns:** A list of attributes associated with the object type, including details like attribute ID, type, and default values.

11. **`create_object(object_type_id, attributes, ...)`**
    - **Description:** Creates a new object with specified attributes.
    - **Parameters:**
      - `object_type_id` (int): ID of the object type.
      - `attributes` (list): List of attribute dictionaries for the new object.
    - **Returns:** A dictionary containing details of the created object, including object ID, type, and attributes.

12. **`update_object(object_id, object_type_id, attributes, ...)`**
    - **Description:** Updates an existing object with new attributes.
    - **Parameters:** Similar to `create_object`, with an additional `object_id` for identifying the object.
    - **Returns:** A dictionary with updated object details.

13. **`delete_object(object_id)`**
    - **Description:** Deletes an object by its ID.
    - **Parameters:**
      - `object_id` (int): The ID of the object to delete.
    - **Returns:** A confirmation message or status indicating successful deletion.

14. **`get_object_attributes(object_id)`**
    - **Description:** Retrieves attributes of a specific object.
    - **Parameters:**
      - `object_id` (int): ID of the object.
    - **Returns:** A dictionary with attribute details, including values, types, and other metadata.

15. **`get_object_history(object_id, ...)`**
    - **Description:** Retrieves the history of changes for a specified object.
    - **Parameters:** Options to filter by ascending order or abbreviation.
    - **Returns:** A list of historical changes, including date, author, and attribute modifications.

16. **`get_object_reference_info(object_id)`**
    - **Description:** Gets references to and from a specified object.
    - **Parameters:**
      - `object_id` (int): ID of the object.
    - **Returns:** A dictionary of related objects and their reference types.

17. **`get_status_types(object_schema_id)`**
    - **Description:** Retrieves available status types for a schema.
    - **Parameters:**
      - `object_schema_id` (int): Optional schema ID for filtering status types.
    - **Returns:** A list of status types, including status ID, name, and description.

18. **`get_attachments_of_objects(object_id)`** *(Data Center only)*
    - **Description:** Fetches attachment details for an object (not supported in Cloud).
    - **Parameters:**
      - `object_id` (int): ID of the object.
    - **Returns:** A list of attachment details like attachment ID, name, and URL.

19. **`upload_attachment_to_object(object_id, filename)`** *(Data Center only)*
    - **Description:** Uploads an attachment to an object (not supported in Cloud).
    - **Parameters:**
      - `object_id` (int): ID of the object.
      - `filename` (str): Path of the file to upload.
    - **Returns:** Details of the uploaded attachment, such as attachment ID and URL.

20. **`delete_attachment(attachment_id)`** *(Data Center only)*
    - **Description:** Deletes an attachment by its ID (not supported in Cloud).
    - **Parameters:**
      - `attachment_id` (int): ID of the attachment.
    - **Returns:** A confirmation of successful deletion.

21. **`add_comment_to_object(comment, object_id, role)`** *(Data Center only)*
    - **Description:** Adds a comment to an object (not supported in Cloud).
    - **Parameters:** Comment text, object ID, and role.
    - **Returns:** Details of the added comment.

22. **`get_comment_of_object(object_id)`** *(Data Center only)*
    - **Description:** Retrieves comments for an object (not supported in Cloud).
    - **Parameters:** Object ID.
    - **Returns:** A list of comments associated with the object.

23. **`get_icon_by_id(icon_id)`**
    - **Description:** Retrieves an icon's details by its ID.
    - **Parameters:**
      - `icon_id` (int): ID of the icon.
    - **Returns:** Icon information including ID, name, and image data or URL.

24. **`get_all_global_icons()`**
    - **Description:** Retrieves all global icons.

    - **Returns:** list of all icons available globally, including details like icon ID, name, and URL.

26. **`start_import_configuration(import_id)`**
    - **Description:** Starts an import based on a configuration ID.
    - **Parameters:**
      - `import_id` (int): ID of the import configuration.
    - **Returns:** Status or confirmation of the import initiation.

27. **`reindex_insight()`** *(Data Center only)*
    - **Description:** Initiates a full reindex of Insight (not supported in Cloud).
    - **Returns:** Confirmation of the reindex operation.

28. **`reindex_current_node_insight()`** *(Data Center only)*
    - **Description:** Reindexes the current node in Insight (not supported in Cloud).
    - **Returns:** Confirmation of the reindex operation for the current node.
    
