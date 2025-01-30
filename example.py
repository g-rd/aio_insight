import asyncio
import json
import logging
from typing import Dict, Any, Optional, List

from aio_insight.aio_insight import AsyncInsight
from aio_insight.graph_builder import create_schema_structure
from creds import assets_token, assets_url, assets_username

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_schema(session: AsyncInsight, schema_name: str = "Assets") -> Optional[Dict[str, Any]]:
    try:
        schemas = await session.get_object_schemas()

        for schema in schemas.get('objectschemas', []) if 'objectschemas' in schemas else schemas.get('values', []):
            if schema['name'] == schema_name:
                return schema
        return None
    except Exception as e:
        logger.error(f"Error getting schema: {str(e)}")
        return None
                

async def get_schema_payload(session: AsyncInsight, schema_name: str = "Assets") -> Optional[Dict[str, Any]]:
    """
    Get the complete schema payload for a given schema name.

    Args:
        session (AsyncInsight): The AsyncInsight session
        schema_name (str): Name of the schema to get payload for

    Returns:
        Optional[Dict[str, Any]]: Complete schema payload or None if schema not found
    """
    try:
        schemas = await session.get_object_schemas()

        for schema in schemas.get('objectschemas', []) if 'objectschemas' in schemas else schemas.get('values', []):
            schema_id = schema['id']
            if schema['name'] != schema_name:
                continue

            # Get all object types for this schema
            object_types = await session.get_object_schema_object_types(schema_id)
            print(f"Getting attributes for schema {schema_id}")
            print(f"Object types: {object_types}")

            schema_payload = {
                "schema": {
                    "name": schema['name'],
                    "description": schema.get('description', ''),
                    "objectSchemaKey": schema.get('objectSchemaKey'),
                    "status": schema.get('status', 'ENABLED')
                },
                "objectTypes": []
            }

            # Get attributes for each object type
            for obj_type in object_types:
                type_id = obj_type['id']
                attributes = await session.get_object_type_attributes(type_id, include_children=False, exclude_parent_attributes=True)
                print(f"Getting attributes for object type {obj_type.get("name")} ID: {type_id}")
                print(f"\"{obj_type.get("name")}\" Attributes: \"{[attr.get("name") for attr in attributes]}\"")

                object_type_payload = {
                    "id": obj_type['id'],
                    "name": obj_type['name'],
                    "type": obj_type.get('type', 0),
                    "description": obj_type.get('description', ''),
                    "icon": obj_type.get('icon', ''),
                    "position": obj_type.get('position', 0),
                    "parentObjectTypeId": obj_type.get('parentObjectTypeId'),
                    "attributes": []
                }

                # Add attributes
                for attr in attributes:
                    attribute_payload = {
                        "name": attr['name'],
                        "type": attr['type'],
                        "description": attr.get('description', ''),
                        "defaultType": attr.get('defaultType'),
                        "required": attr.get('required', False),
                        "minimumCardinality": attr.get('minimumCardinality', 0),
                        "maximumCardinality": attr.get('maximumCardinality', 0),
                    }

                    if attr['type'] == 1:  # Reference type
                        attribute_payload.update({
                            "referenceType": {
                                "objectTypeId": attr['referenceObjectType']['id'],
                                "objectSchemaId": attr['referenceObjectType']['objectSchemaId']
                            }
                        })
                    elif attr['type'] == 0 and 'objectType' in attr:  # Custom type
                        attribute_payload.update({
                            "customType": {
                                "type": attr['objectType'].get('type'),
                                "configuration": attr['objectType'].get('configuration', {})
                            }
                        })

                    object_type_payload["attributes"].append(attribute_payload)

                schema_payload["objectTypes"].append(object_type_payload)

            return schema_payload

        return None
    except Exception as e:
        logger.error(f"Error getting schema payload: {str(e)}")
        raise


async def create_new_schema(session: AsyncInsight, schema_payload: Dict[str, Any], new_name: str) -> Dict[str, Any]:
    schema_key = ''.join(c.upper() for c in new_name if c.isalnum())[:10]
    if len(schema_key) < 2:
        schema_key = schema_key + 'X' * (2 - len(schema_key))

    logger.info(f"Using schema key: {schema_key}")

    logger.info(f"Checking if schema {new_name} already exists")
    list_schemas = await session.get_object_schemas()
    schema_exists = False
    new_schema = None
    new_schema_id = None
    object_types = []

    for schema in list_schemas.get('objectschemas', []) if 'objectschemas' in list_schemas else list_schemas.get('values', []):
        if isinstance(schema, dict) and schema.get('name') == new_name:
            logger.info(f"Schema {new_name} already exists")
            schema_exists = True
            new_schema = schema
            new_schema_id = new_schema.get("id")
            object_types = schema_payload.get("objectTypes", [])
            break
            
    if not schema_exists:
        try:
            new_schema = await session.create_object_schema(
                name=new_name,
                description=schema_payload["schema"].get("description", ""),
                object_schema_key=schema_key
            )
            logger.info(f"Created new schema: {new_schema}")
        except Exception as e:
            logger.warning(f"Schema creation error: {str(e)}")
            schemas = await session.get_object_schemas()
            schemas_list = schemas.get('objectschemas', []) or schemas.get('values', [])
    
            for schema in schemas_list:
                if isinstance(schema, dict) and schema.get('name') == new_name:
                    new_schema = schema
                    logger.info(f"Found existing schema: {schema.get('name')}")
                    break
            else:
                raise ValueError(f"Could not create or find schema {new_name}")
    
        if new_schema:
            new_schema_id = new_schema.get("id")
            logger.info(f"Working with schema ID: {new_schema_id}")
            object_types = schema_payload.get("objectTypes", [])
            
        if not object_types:
            logger.warning("No object types found in schema payload")
            return new_schema

    if new_schema_id is None:
        raise ValueError("Schema ID not initialized")

    logger.info(f"Processing {len(object_types)} object types")

    ordered_nodes = create_schema_structure(object_types)
    nodes_created = []
    objects_created = {}

    current_objects = await session.get_object_types(new_schema_id)
    current_object_types = [obj.get("name") for obj in current_objects if isinstance(obj, dict)]

    for node in ordered_nodes:
        if node not in nodes_created and node.get('name') not in current_object_types:
            nodes_created.append(node)
            print(f"Creating object type: {node.get('name')}")
            icon_data = node.get('icon', {})
            icon_id = icon_data.get('id') if isinstance(icon_data, dict) else icon_data

            parent_id = objects_created.get(node.get('parent_name'))
            print(f"Found parent object type ID: {parent_id}, for object type: {node.get('name')} with parent: {node.get('parent_name')} ")

            new_object_type = await session.create_object_type(
                schema_id=new_schema_id,
                name=node.get('name'),
                description=node.get('description'),
                icon_id=icon_id,
                parent_object_type_id=parent_id
            )

            objects_created[node.get('name')] = new_object_type.get('id')
            print(f"Created object type: {new_object_type}")

    # Create attributes
    for node in ordered_nodes:
        object_type_id = next(
            (obj.get("id") for obj in current_objects
             if isinstance(obj, dict) and obj.get("name") == node.get('name')),
            None
        )

        if not object_type_id:
            logger.warning(f"Could not find object type ID for {node.get('name')}")
            continue

        # Get existing attributes for this object type
        try:
            existing_attributes = await session.get_object_type_attributes(object_type_id)
            existing_attribute_names = {attr.get('name').lower() for attr in existing_attributes if isinstance(attr, dict)}
            logger.info(f"Found existing attributes for {node.get('name')}: {existing_attribute_names}")
        except Exception as e:
            logger.error(f"Error fetching existing attributes: {str(e)}")
            existing_attribute_names = set()

        parent_name = next(
            (obj.get("name") for obj in current_objects if obj.get("name") == node.get('parent_name')),
            None
        )

        parent_attributes = []
        default_attributes = {'Key', 'Name', 'Created', 'Updated'}

        if parent_name:
            for obj in ordered_nodes:
                if obj.get("name") == parent_name:
                    print(f"object type: {node.get('name')}, parent name: {parent_name}")
                    parent_attributes = obj.get("attributes", [])
                    parent_attribute_names = [attr.get("name") for attr in parent_attributes if isinstance(attr, dict)]
                    print(f"Parent attribute name: \"{parent_name}\" Parent attributes: {parent_attribute_names}")

        # Filter out existing attributes from attribute_payloads
        attribute_payloads = [
            attr for attr in node.get("attributes", [])
            if attr.get('name') and attr.get('name').lower() not in existing_attribute_names
            and attr.get('name') not in default_attributes
        ]

        print(f"Processing {len(attribute_payloads)} new attributes for object type: {node.get('name')}")
        for attr in attribute_payloads:
            # Check if attribute exists in parent attributes
            if parent_attributes and attr['name'] in [p_attr.get('name') for p_attr in parent_attributes]:
                logger.info(f"Skipping attribute {attr['name']} as it exists in parent")
                continue
                
            print(f"Creating attribute: {attr}")

            # Prepare attribute payload
            attribute_payload = {
                "object_type_id": object_type_id,
                "name": attr["name"],
                "type": attr.get("type", 0),
                "description": attr.get("description", ""),
                "label": bool(attr.get("label", False)),
                "min_cardinality": int(attr.get("minimumCardinality", 0)),
                "max_cardinality": int(attr.get("maximumCardinality", 1)),
                "suffix": attr.get("suffix"),
                "include_child_object_types": bool(attr.get("includeChildObjectTypes", False)),
                "hidden": bool(attr.get("hidden", False)),
                "unique_attribute": bool(attr.get("uniqueAttribute", False)),
                "summable": bool(attr.get("summable", False))
            }

            # Handle Object reference type (type=1)
            if attr.get("type") == 1:
                if attr.get("referenceType") and attr["referenceType"].get("objectTypeId"):
                    old_ref_type_id = attr["referenceType"]["objectTypeId"]
                    old_ref_type_name = attr["referenceType"]
                    print(f"Found reference type: {old_ref_type_name} for attribute {attr['name']}" )
                    
                    # First try to get the reference type from existing objects
                    reference_type = next(
                        (obj for obj in current_objects 
                         if obj.get("id") == old_ref_type_id),
                        None
                    )

                    print(f"Found reference type: {reference_type} for attribute {attr['name']}" )

                    if reference_type:
                        # Use the existing reference type ID
                        attribute_payload["type_value"] = str(reference_type["id"])
                        logger.info(f"Using existing reference type ID {reference_type['id']} for attribute {attr['name']}")
                    else:
                        # Try to find the mapped ID from objects_created
                        reference_type_name = next(
                            (node.get('name') for node in ordered_nodes 
                             if node.get('id') == old_ref_type_id),
                            None
                        )
                        
                        if reference_type_name and reference_type_name in objects_created:
                            current_ref_type_id = objects_created[reference_type_name]
                            attribute_payload["type_value"] = str(current_ref_type_id)
                            logger.info(f"Mapped reference type ID from {old_ref_type_id} to {current_ref_type_id} for attribute {attr['name']}")
                        else:
                            # If we can't find the reference type, log and skip
                            logger.warning(f"Could not find reference type for attribute {attr['name']} (old ID: {old_ref_type_id})")
                            continue
                else:
                    logger.warning(f"Skipping attribute {attr['name']} - missing referenceType.objectTypeId")
                    continue

            # Handle default type if present
            if attr.get("defaultType"):
                if isinstance(attr["defaultType"], dict) and "id" in attr["defaultType"]:
                    attribute_payload["default_type_id"] = attr["defaultType"]["id"]
                elif isinstance(attr["defaultType"], int):
                    attribute_payload["default_type_id"] = attr["defaultType"]

            # Only add these fields if they have valid values
            if attr.get("typeValueMulti"):
                attribute_payload["type_value_multi"] = attr["typeValueMulti"]
            if attr.get("additionalValue"):
                attribute_payload["additional_value"] = attr["additionalValue"]
            if attr.get("regexValidation"):
                attribute_payload["regex_validation"] = attr["regexValidation"]
            if attr.get("qlQuery"):
                attribute_payload["ql_query"] = attr["qlQuery"]
            if attr.get("options"):
                attribute_payload["options"] = attr["options"]

            # Remove None values to avoid API issues
            attribute_payload = {k: v for k, v in attribute_payload.items() if v is not None}
            
            print(f"Creating attribute: {attr.get('name')} with payload: {attribute_payload}")

            try:
                # await session.create_object_type_attribute(**attribute_payload)
                logger.info(f"Created attribute: {attr['name']}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.error(f"Error creating attribute {attr['name']}: {str(e)}")

    return new_schema

    
def build_hierarchical_graph(object_types, schema_name):
    """
    Builds a hierarchical graph structure from object types with cycle detection.
    Args:
        object_types: List of object type dictionaries
        schema_name: Name of the schema
    Returns:
        Dictionary representing the hierarchical graph structure
    """
    # Initialize the root structure
    graph = {
        schema_name: {
            "name": schema_name,
            "parentObjectTypeId": None,
            "schemaId": 1,
            "nodes": []
        }
    }
    
    # Create mappings for easier lookup with safety check
    id_to_obj = {}
    for obj in object_types:
        if isinstance(obj, dict) and 'id' in obj:
            id_to_obj[obj['id']] = obj
    
    # Keep track of visited nodes to prevent cycles
    visited = set()
    
    def get_children(parent_id, path=None):
        """
        Helper function to get all children of a parent ID
        Args:
            parent_id: ID of the parent node
            path: Set of node IDs in current path for cycle detection
        """
        if path is None:
            path = set()
            
        # Check for cycles
        if parent_id in path:
            print(f"Warning: Cycle detected at node {parent_id}")
            return []
            
        # Add current node to path
        path.add(parent_id)
        children = []
        
        for obj in object_types:
            if not isinstance(obj, dict):
                continue
                
            if obj.get("parentObjectTypeId") == parent_id:
                obj_id = obj.get("id")
                
                # Skip if we've already processed this node
                if obj_id in visited:
                    continue
                    
                visited.add(obj_id)
                child_node = {
                    obj.get("name", "Unknown"): {
                        "id": obj_id,
                        "name": obj.get("name", "Unknown"),
                        "parentObjectTypeId": obj.get("parentObjectTypeId"),
                        "abstractObjectType": obj.get("abstractObjectType", False)
                    }
                }
                
                # Recursively get children with current path
                child_children = get_children(obj_id, path.copy())
                if child_children:
                    child_node[obj.get("name", "Unknown")]["nodes"] = child_children
                
                children.append(child_node)
        
        return children

    # Get all root level nodes (nodes with no parent)
    root_nodes = []
    for obj in object_types:
        if not isinstance(obj, dict):
            continue
            
        if obj.get("parentObjectTypeId") is None:
            obj_id = obj.get("id")
            if obj_id not in visited:
                visited.add(obj_id)
                root_node = {
                    obj.get("name", "Unknown"): {
                        "id": obj_id,
                        "name": obj.get("name", "Unknown"),
                        "parentObjectTypeId": None,
                        "abstractObjectType": obj.get("abstractObjectType", False)
                    }
                }
                
                # Get children for this root node
                children = get_children(obj_id, {obj_id})
                if children:
                    root_node[obj.get("name", "Unknown")]["nodes"] = children
                
                root_nodes.append(root_node)

    # Add root nodes to the main graph
    graph[schema_name]["nodes"] = root_nodes
    
    return graph

def topological_sort(object_types, schema_name="Asset New"):
    """
    Performs a topological sort and returns a hierarchical graph structure.
    """
    print("\n=== Starting Topological Sort ===")
    print(f"Input object types: {[obj['name'] for obj in object_types]}")
    
    # Build the hierarchical graph
    graph = build_hierarchical_graph(object_types, schema_name)
    
    # For debugging, print the resulting structure
    print("\n=== Resulting Graph Structure ===")
    print(json.dumps(graph, indent=2))
    
    return graph

async def main():
    async with AsyncInsight(
            url=assets_url,
            username=assets_username,
            token=assets_token,
            verify_ssl=False,
            cloud=False
    ) as session:
        # Get the existing schema payload
        schema_payload = await get_schema_payload(session, "Assets")
        if schema_payload:
            # Create new schema with the payload
            new_schema = await create_new_schema(session, schema_payload, "Assets New")
        #     print("\n=== New Schema Created ===")
        #     print(f"Schema ID: {new_schema['id']}")
        #     print(f"Schema Name: {new_schema['name']}")
        #     print("========================\n")
        # else:
        #     print("Original schema 'Assets' not found")


if __name__ == "__main__":
    asyncio.run(main())