import logging
from typing import List, Dict, Any
import aiofiles
import httpx

from aio_insight.aio_api_client import RateLimitedAsyncAtlassianRestAPI, RateLimiter

log = logging.getLogger(__name__)

class AsyncInsight(RateLimitedAsyncAtlassianRestAPI):
    def __init__(
        self,
        *,
        url: str,
        username: str,
        password: str,
        cloud: bool = False,
        **kwargs
    ):
        """
        Initialize the AsyncInsight client.

        Args:
            url (str): Base URL of your Jira instance.
            username (str): Username or email for authentication.
            password (str): API token or password for authentication.
            cloud (bool): Set to True if using Jira Cloud; False for Data Center/on-premise.
            **kwargs: Additional keyword arguments for the parent class.
        """
        super().__init__(
            url=url,
            username=username,
            password=password,
            **kwargs
        )
        self.cloud = cloud
        self.default_headers = {
            "Accept": "application/json",
        }
        self.workspace_id = None
        self.api_url = None
        self.api_root = None

    async def __aenter__(self):
        if self.cloud:
            await self._initialize_cloud()
        else:
            await self._initialize_datacenter()
        return await super().__aenter__()

    async def _initialize_cloud(self):
        """
        Initializes the client for Jira Cloud by retrieving the workspace ID
        and setting the appropriate base URL and API root.
        """
        # Retrieve the workspace ID
        self.workspace_id = await self._get_workspace_id()
        # Set the base URL for API calls to https://api.atlassian.com
        self.api_url = "https://api.atlassian.com"
        # Set the API root to include the workspace ID
        self.api_root = f"jsm/assets/workspace/{self.workspace_id}/v1"

        # Include basic auth headers
        auth_header = httpx.BasicAuth(self.username, self.password)
        self._session.auth = auth_header

    async def _initialize_datacenter(self):
        """
        Initializes the client for Jira Data Center by setting the base URL and API root.
        """
        # Set the base URL to the provided Jira URL
        self.api_url = self.url
        # Set the API root for Data Center
        self.api_root = "rest/insight/1.0"

        # Include basic auth headers
        auth_header = httpx.BasicAuth(self.username, self.password)
        self._session.auth = auth_header

    async def _get_workspace_id(self):
        """
        Retrieves the workspace ID for Assets Cloud.
        """
        url = self.url_joiner(self.url, "rest/servicedeskapi/assets/workspace")
        response = await self.get(url, absolute=True)
        return response["values"][0]["workspaceId"]

    async def get_object_schemas(self) -> Dict[str, Any]:
        """
        Retrieves information about all object schemas.
        """
        url = self.url_joiner(self.api_root, "objectschema/list")
        result = await self.get(url)
        return result

    async def get_object_schema(self, schema_id: int) -> Dict[str, Any]:
        """
        Retrieves information about an object schema based on its ID.

        Args:
            schema_id (int): The ID of the object schema.

        Returns:
            dict: The details of the specified object schema.
        """
        url = self.url_joiner(self.api_root, f"objectschema/{schema_id}")
        result = await self.get(url)
        return result

    async def create_object_schema(self, name: str, description: str) -> Dict[str, Any]:
        """
        Creates a new object schema with the specified name and description.

        Args:
            name (str): The name of the new object schema.
            description (str): The description of the new object schema.

        Returns:
            dict: The response from the API after creating the object schema.
        """
        url = self.url_joiner(self.api_root, "objectschema/create")
        body = {"name": name, "description": description}
        return await self.post(url, json=body)

    async def update_object_schema(self, schema_id: int, name: str, description: str) -> Dict[str, Any]:
        """
        Updates an object schema based on the provided schema ID.

        Args:
            schema_id (int): The ID of the object schema to update.
            name (str): The new name for the object schema.
            description (str): The new description for the object schema.

        Returns:
            dict: The response from the API after updating the object schema.
        """
        url = self.url_joiner(self.api_root, f"objectschema/{schema_id}")
        body = {"name": name, "description": description}
        return await self.put(url, json=body)

    async def get_object_schema_object_types(self, schema_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all object types for a given object schema.

        Args:
            schema_id (int): The ID of the object schema.

        Returns:
            list: A list of object types for the specified schema.
        """
        url = self.url_joiner(
            self.api_root,
            f"objectschema/{schema_id}/objecttypes"
        )
        return await self.get(url)

    async def get_object_schema_object_types_flat(self, schema_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all object types for a given object schema in a flat structure.

        Args:
            schema_id (int): The ID of the object schema.

        Returns:
            list: A flat list of object types for the specified schema.
        """
        url = self.url_joiner(
            self.api_root,
            f"objectschema/{schema_id}/objecttypes/flat"
        )
        return await self.get(url)

    async def get_object_schema_object_attributes(
            self,
            schema_id: int,
            only_value_editable: bool = False,
            order_by_name: bool = False,
            query: str = None,
            include_value_exist: bool = False,
            exclude_parent_attributes: bool = False,
            include_children: bool = False,
            order_by_required: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all attributes under a specified schema across all Jira types.

        Args:
            schema_id (int): The ID of the object schema.
            only_value_editable (bool, optional): If True, only includes attributes where the value is editable. Defaults to False.
            order_by_name (bool, optional): If True, orders the response by name. Defaults to False.
            query (str, optional): Filters attributes that start with the provided query. Defaults to None.
            include_value_exist (bool, optional): If True, only includes attributes where attribute values exist. Defaults to False.
            exclude_parent_attributes (bool, optional): If True, excludes parent attributes. Defaults to False.
            include_children (bool, optional): If True, includes child attributes. Defaults to False.
            order_by_required (bool, optional): If True, orders the response by the number of required attributes. Defaults to False.

        Returns:
            list: A list of attributes under the requested schema.
        """
        url = self.url_joiner(
            self.api_root,
            f"objectschema/{schema_id}/attributes"
        )

        params = {
            'onlyValueEditable': only_value_editable,
            'orderByName': order_by_name,
            'includeValueExist': include_value_exist,
            'excludeParentAttributes': exclude_parent_attributes,
            'includeChildren': include_children,
            'orderByRequired': order_by_required
        }
        if query:
            params['query'] = query

        params = {k: v for k, v in params.items() if v not in (False, None)}

        return await self.get(url, params=params)

    async def get_object(self, object_id: int) -> Dict[str, Any]:
        """
        Retrieves information about a specific object by its ID.

        Args:
            object_id (int): The ID of the object.

        Returns:
            dict: The details of the specified object.
        """
        url = self.url_joiner(self.api_root, f"object/{object_id}")
        result = await self.get(url)
        return result

    async def get_objects_by_aql(
        self,
        schema_id: int,
        object_type_id: int,
        aql_query: str,
        page: int = 1,
        results_per_page: int = 25,
        include_attributes: bool = True,
    ) -> Dict[str, Any]:
        """
        Retrieves a list of objects based on an AQL query.

        Args:
            schema_id (int): The ID of the schema.
            object_type_id (int): The ID of the object type.
            aql_query (str): The AQL query string.
            page (int, optional): The page number (default is 1).
            results_per_page (int, optional): Number of results per page (default is 25).
            include_attributes (bool, optional): Should object attributes be included in the response. Defaults to True.

        Returns:
            dict: The response containing matching objects.
        """
        payload = {
            "objectTypeId": object_type_id,
            "page": page,
            "asc": True,
            "resultsPerPage": results_per_page,
            "includeAttributes": include_attributes,
            "objectSchemaId": schema_id,
            "qlQuery": aql_query,
        }

        url = self.url_joiner(self.api_root, "object/navlist/aql")

        result = await self.post(url, json=payload)
        return result

    async def get_object_type_attributes(
        self,
        object_type_id: int,
        only_value_editable: bool = False,
        order_by_name: bool = False,
        query: str = None,
        include_value_exist: bool = False,
        exclude_parent_attributes: bool = False,
        include_children: bool = True,
        order_by_required: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Fetches all object type attributes for a given object type.

        Args:
            object_type_id (int): The ID of the object type.
            only_value_editable (bool): If True, only includes attributes where only the value is editable. Defaults to False.
            order_by_name (bool): If True, orders the response by name. Defaults to False.
            query (str): Filters attributes that start with the provided query string. Defaults to None.
            include_value_exist (bool): If True, includes only attributes where attribute values exist. Defaults to False.
            exclude_parent_attributes (bool): If True, excludes parent attributes from the response. Defaults to False.
            include_children (bool): If True, includes child attributes in the response. Defaults to True.
            order_by_required (bool): If True, orders the response by the number of required attributes. Defaults to False.

        Returns:
            list: The result from the API call.
        """
        params = {
            "onlyValueEditable": only_value_editable,
            "orderByName": order_by_name,
            "includeValueExist": include_value_exist,
            "excludeParentAttributes": exclude_parent_attributes,
            "includeChildren": include_children,
            "orderByRequired": order_by_required,
        }

        if query:
            params["query"] = query

        params = {k: v for k, v in params.items() if v not in (False, None)}

        url = self.url_joiner(self.api_root, f"objecttype/{object_type_id}/attributes")
        return await self.get(url, params=params)

    async def create_object(
        self,
        object_type_id: int,
        attributes: List[Dict[str, Any]],
        has_avatar: bool = False,
        avatar_uuid: str = ""
    ) -> Dict[str, Any]:
        """
        Creates a new object with the specified attributes.

        Args:
            object_type_id (int): The ID of the object type for the new object.
            attributes (List[dict]): A list of attributes for the new object.
            has_avatar (bool): Indicates if the object has an avatar. Defaults to False.
            avatar_uuid (str): The UUID of the avatar, if applicable. Defaults to an empty string.

        Returns:
            dict: The response from the API after creating the object.
        """
        data = {
            "attributes": attributes,
            "objectTypeId": object_type_id,
            "avatarUUID": avatar_uuid,
            "hasAvatar": has_avatar,
        }
        url = self.url_joiner(self.api_root, "object/create")
        response = await self.post(url, json=data)

        return response

    async def update_object(
        self,
        object_id: int,
        object_type_id: int,
        attributes: List[Dict[str, Any]],
        has_avatar: bool = False,
        avatar_uuid: str = "",
    ) -> Dict[str, Any]:
        """
        Updates an object with new data.

        Args:
            object_id (int): The ID of the object to update.
            object_type_id (int): The ID of the object type.
            attributes (List[dict]): A list of attributes to update on the object.
            has_avatar (bool): Indicates if the object has an avatar. Defaults to False.
            avatar_uuid (str): The UUID of the avatar, if applicable. Defaults to an empty string.

        Returns:
            dict: The response from the API after updating the object.
        """
        body = {
            "attributes": attributes,
            "objectTypeId": object_type_id,
            "avatarUUID": avatar_uuid,
            "hasAvatar": has_avatar,
        }
        url = self.url_joiner(self.api_root, f"object/{object_id}")
        return await self.put(url, json=body)

    async def delete_object(self, object_id: int) -> Dict[str, Any]:
        """
        Deletes an object based on its ID.

        Args:
            object_id (int): The ID of the object to delete.

        Returns:
            dict: The response from the API after deleting the object.
        """
        url = self.url_joiner(self.api_root, f"object/{object_id}")
        return await self.delete(url)

    async def get_object_attributes(self, object_id: int) -> Dict[str, Any]:
        """
        Retrieves attributes of an object.

        Args:
            object_id (int): The ID of the object to retrieve attributes for.

        Returns:
            dict: The object's attributes returned by the API.
        """
        url = self.url_joiner(self.api_root, f"object/{object_id}/attributes")
        return await self.get(url)

    async def get_object_history(
            self,
            object_id: int,
            asc: bool = False,
            abbreviate: bool = True
    ) -> Dict[str, Any]:
        """
        Fetches the history of an object.

        Args:
            object_id (int): The ID of the object whose history is to be fetched.
            asc (bool): If True, orders the history in ascending order. Defaults to False.
            abbreviate (bool): If True, abbreviates the history. Defaults to True.

        Returns:
            dict: The history of the object as returned by the API.
        """
        params = {"asc": asc, "abbreviate": abbreviate}
        url = self.url_joiner(self.api_root, f"object/{object_id}/history")
        return await self.get(url, params=params)

    async def get_object_reference_info(self, object_id: int) -> Dict[str, Any]:
        """
        Retrieves reference information for an object.

        Args:
            object_id (int): The ID of the object to retrieve reference information for.

        Returns:
            dict: Reference information for the object, as returned by the API.
        """
        url = self.url_joiner(self.api_root, f"object/{object_id}/referenceinfo")
        return await self.get(url)

    async def get_status_types(self, object_schema_id: int = None) -> Dict[str, Any]:
        """
        Retrieves status types for a given object schema ID.

        Args:
            object_schema_id (int, optional): The ID of the object schema. If not provided,
                                              it will return all global statuses.

        Returns:
            dict: A list of status type objects.
        """
        url = self.url_joiner(self.api_root, "config/statustype")

        params = {}
        if object_schema_id is not None:
            params['objectSchemaId'] = object_schema_id

        result = await self.get(url, params=params)
        return result

    # Methods not supported in cloud instances
    async def get_attachments_of_objects(self, object_id: int):
        """
        Fetches attachment information for a specified object ID.

        Args:
            object_id (int): The ID of the object to retrieve attachments for.

        Returns:
            list: A list of attachment information objects.
        """
        if self.cloud:
            raise NotImplementedError("This method is not supported in Insight Cloud.")
        url = self.url_joiner(
            self.api_root,
            f"attachments/object/{object_id}",
        )
        return await self.get(url)

    async def upload_attachment_to_object(self, object_id: int, filename: str) -> Dict[str, Any]:
        """
        Uploads an attachment to a specified object.

        Args:
            object_id (int): The ID of the object to attach the file to.
            filename (str): The path to the file to be uploaded.

        Returns:
            dict: The response from the API after uploading the attachment.
        """
        if self.cloud:
            raise NotImplementedError("This method is not supported in Insight Cloud.")
        log.warning("Adding attachment...")
        url = f"rest/insight/1.0/attachments/object/{object_id}"
        async with aiofiles.open(filename, "rb") as attachment:
            files = {"file": await attachment.read()}
            return await self.post(url, headers=self.no_check_headers, files=files)

    async def delete_attachment(self, attachment_id: int) -> Dict[str, Any]:
        """
        Deletes an attachment based on the provided attachment ID.

        Args:
            attachment_id (int): The ID of the attachment to be deleted.

        Returns:
            dict: The response from the API after deleting the attachment.
        """
        if self.cloud:
            raise NotImplementedError("This method is not supported in Insight Cloud.")
        log.warning("Deleting attachment...")
        url = f"rest/insight/1.0/attachments/{attachment_id}"
        return await self.delete(url)

    async def add_comment_to_object(self, comment: str, object_id: int, role: str) -> Dict[str, Any]:
        """
        Adds a comment to a specified object.

        Args:
            comment (str): The comment text to be added.
            object_id (int): The ID of the object to add the comment to.
            role (str): The role associated with the comment.

        Returns:
            dict: The response from the API after adding the comment.
        """
        if self.cloud:
            raise NotImplementedError("This method is not supported in Insight Cloud.")
        params = {"comment": comment, "objectId": object_id, "role": role}
        url = "rest/insight/1.0/comment/create"
        return await self.post(url, params=params)

    async def get_comment_of_object(self, object_id: int):
        """
        Retrieves comments for a specified object ID.

        Args:
            object_id (int): The ID of the object to retrieve comments for.

        Returns:
            list: A list of comments associated with the object.
        """
        if self.cloud:
            raise NotImplementedError("This method is not supported in Insight Cloud.")
        url = f"rest/insight/1.0/comment/object/{object_id}"
        return await self.get(url)

    async def get_icon_by_id(self, icon_id: int) -> Dict[str, Any]:
        """
        Retrieves information about an icon by its ID.

        Args:
            icon_id (int): The ID of the icon.

        Returns:
            dict: Icon information.
        """
        url = self.url_joiner(self.api_root, f"icon/{icon_id}")
        return await self.get(url)

    async def get_all_global_icons(self) -> List[Dict[str, Any]]:
        """
        Retrieves information about all global icons.

        Returns:
            list: A list of global icons.
        """
        url = self.url_joiner(self.api_root, "icon/global")
        return await self.get(url)

    async def start_import_configuration(self, import_id: int) -> Dict[str, Any]:
        """
        Starts the import process for a given import configuration.

        Args:
            import_id (int): The ID of the import configuration.

        Returns:
            dict: The response from the API after starting the import.
        """
        url = self.url_joiner(
            self.api_root,
            f"import/start/{import_id}",
        )
        return await self.post(url)

    async def reindex_insight(self) -> Dict[str, Any]:
        """
        Initiates reindexing of Insight.

        Returns:
            dict: The response from the API after starting the reindexing.
        """
        if self.cloud:
            raise NotImplementedError("This method is not supported in Insight Cloud.")
        url = self.url_joiner(self.api_root, "index/reindex/start")
        return await self.post(url)

    async def reindex_current_node_insight(self) -> Dict[str, Any]:
        """
        Initiates reindexing of the current node in Insight.

        Returns:
            dict: The response from the API after starting the reindexing for the current node.
        """
        if self.cloud:
            raise NotImplementedError("This method is not supported in Insight Cloud.")
        url = self.url_joiner(self.api_root, "index/reindex/currentnode")
        return await self.post(url)

    # Deprecated methods can be removed or adjusted accordingly
    # For example, removing deprecated methods or updating them

