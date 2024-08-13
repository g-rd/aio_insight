import asyncio

import pytest
import json
from unittest.mock import Mock
from httpx import Response

from aio_insight.aio_insight import AsyncInsight


# Helper function to load JSON fixtures
def load_fixture(filename):
    with open(f"tests/fixtures/{filename}", "r") as f:
        return json.load(f)

@pytest.fixture
def mock_session():
    return Mock()

@pytest.fixture
def insight_client(mock_session):
    return AsyncInsight(url="https://example.com", username="user", password="pass", session=mock_session)


@pytest.mark.asyncio
async def test_get_object_schema(insight_client, mock_session):
    # Arrange
    schema_id = 8
    fixture_data = load_fixture("get_object_schema.json")
    mock_response = Response(200, json=fixture_data)
    mock_session.request.return_value = asyncio.Future()
    mock_session.request.return_value.set_result(mock_response)

    # Act
    result = await insight_client.get_object_schema(schema_id)

    # Assert
    mock_session.request.assert_called_once_with(
        method="GET",
        url=f"https://example.com/rest/insight/1.0/objectschema/{schema_id}",
        headers=insight_client.default_headers,
        data=None,
        json=None,
        files=None,
    )
    assert result == fixture_data


@pytest.mark.asyncio
async def test_get_object_schema_object_types(insight_client, mock_session):
    # Arrange
    schema_id = 8
    fixture_data = load_fixture("get_object_schema_object_types.json")
    mock_response = Response(200, json=fixture_data)

    future = asyncio.Future()
    future.set_result(mock_response)
    mock_session.request.return_value = future

    # Act
    result = await insight_client.get_object_schema_object_types(schema_id)

    # Assert
    mock_session.request.assert_called_once_with(
        method="GET",
        url=f"https://example.com/rest/insight/1.0/objectschema/{schema_id}/objecttypes",
        headers=insight_client.default_headers,
        data=None,
        json=None,
        files=None,
    )
    assert result == fixture_data

    # Additional assertions
    assert len(result) == 2
    assert result[0]["name"] == "Namespace"
    assert result[1]["name"] == "Image"
    assert all("example.com" in obj["icon"]["url16"] for obj in result)

@pytest.mark.asyncio
async def test_get_object_schema_object_types_flat(insight_client, mock_session):
    # Arrange
    schema_id = 8
    fixture_data = load_fixture("get_object_schema_object_types_flat.json")
    mock_response = Response(200, json=fixture_data)

    future = asyncio.Future()
    future.set_result(mock_response)
    mock_session.request.return_value = future

    # Act
    result = await insight_client.get_object_schema_object_types_flat(schema_id)

    # Assert
    mock_session.request.assert_called_once_with(
        method="GET",
        url=f"https://example.com/rest/insight/1.0/objectschema/{schema_id}/objecttypes/flat",
        headers=insight_client.default_headers,
        data=None,
        json=None,
        files=None,
    )
    assert result == fixture_data

    # Additional assertions
    assert len(result) == 25  # Updated to match the actual number of items

    # Check for specific object types
    object_type_names = [obj['name'] for obj in result]
    assert 'Namespace' in object_type_names
    assert 'Image' in object_type_names
    assert 'Assets' in object_type_names
    assert 'Physical Host' in object_type_names
    assert 'Virtual Host' in object_type_names
    assert 'Network' in object_type_names

    # Check for specific attributes
    assert all('id' in obj for obj in result)
    assert all('name' in obj for obj in result)
    assert all('type' in obj for obj in result)
    assert all('icon' in obj for obj in result)
    assert all('position' in obj for obj in result)
    assert all('created' in obj for obj in result)
    assert all('updated' in obj for obj in result)
    assert all('objectCount' in obj for obj in result)
    assert all('objectSchemaId' in obj for obj in result)
    assert all('inherited' in obj for obj in result)
    assert all('abstractObjectType' in obj for obj in result)
    assert all('parentObjectTypeInherited' in obj for obj in result)

    # Check for specific object type details
    namespace = next(obj for obj in result if obj['name'] == 'Namespace')
    assert namespace['id'] == 178
    assert namespace['icon']['name'] == 'Cube'
    assert namespace['position'] == 0
    assert namespace['objectSchemaId'] == 8

    # Check for abstract object types
    assert any(obj['abstractObjectType'] for obj in result)

    # Check for inherited object types
    assert any(obj['inherited'] for obj in result)

    # Verify icon URLs
    assert all('example.com' in obj['icon']['url16'] for obj in result)
    assert all('example.com' in obj['icon']['url48'] for obj in result)


@pytest.mark.asyncio
async def test_get_object_schema_object_attributes(insight_client, mock_session):
    # Arrange
    schema_id = 8
    fixture_data = load_fixture("get_object_schema_object_attributes.json")
    mock_response = Response(200, json=fixture_data)

    future = asyncio.Future()
    future.set_result(mock_response)
    mock_session.request.return_value = future

    # Act
    result = await insight_client.get_object_schema_object_attributes(schema_id)

    # Assert
    mock_session.request.assert_called_once_with(
        method="GET",
        url=f"https://example.com/rest/insight/1.0/objectschema/{schema_id}/attributes",
        headers=insight_client.default_headers,
        data=None,
        json=None,
        files=None,
    )
    assert result == fixture_data

    # Additional assertions
    assert len(result) == 166  # Corrected number of attributes

    # Check for specific attribute types
    attribute_types = set(attr['type'] for attr in result)
    assert 0 in attribute_types  # Standard attribute type
    assert 1 in attribute_types  # Reference attribute type
    assert 6 in attribute_types  # Project attribute type
    assert 7 in attribute_types  # Status attribute type

    # Check for specific attributes
    assert any(attr['name'] == 'Name' and attr['label'] == True for attr in result)
    assert any(attr['name'] == 'Key' and attr['editable'] == False and attr['system'] == True for attr in result)
    assert any(attr['name'] == 'Created' and attr['type'] == 0 and attr.get('defaultType', {}).get('name') == 'DateTime' for attr in result)
    assert any(attr['name'] == 'Updated' and attr['type'] == 0 and attr.get('defaultType', {}).get('name') == 'DateTime' for attr in result)
    assert any(attr['name'] == 'IP Address' and attr.get('defaultType', {}).get('name') == 'IP Address' for attr in result)

    # Check for reference attributes
    reference_attrs = [attr for attr in result if attr['type'] == 1]
    assert len(reference_attrs) > 0
    reference_attr = reference_attrs[0]
    assert 'referenceType' in reference_attr
    assert 'referenceObjectType' in reference_attr

    # Check for attributes with specific properties
    assert any(attr['name'] == 'Free' and attr.get('suffix') == 'Mb' for attr in result)
    assert any(attr['name'] == 'Description' and attr.get('defaultType', {}).get('name') == 'Textarea' for attr in result)

    # Check for attributes with specific constraints
    assert any(attr['name'] == 'Name' and attr['minimumCardinality'] == 1 and attr['maximumCardinality'] == 1 for attr in result)
    assert any(attr['maximumCardinality'] == -1 for attr in result)  # At least one attribute with no upper limit

    # Check for attributes with specific options
    select_attrs = [attr for attr in result if attr.get('defaultType', {}).get('name') == 'Select']
    if select_attrs:
        assert 'options' in select_attrs[0]

    # Check for boolean attributes
    assert any(attr.get('defaultType', {}).get('name') == 'Boolean' for attr in result)

    # Check for attributes with IQL queries
    iql_attrs = [attr for attr in result if 'iql' in attr]
    if iql_attrs:
        assert isinstance(iql_attrs[0]['iql'], str)

    # Verify that all attributes have common fields
    common_fields = ['id', 'name', 'type', 'editable', 'system', 'sortable', 'summable', 'indexed', 'removable', 'hidden']
    assert all(all(field in attr for field in common_fields) for attr in result)

if __name__ == "__main__":
    pytest.main()