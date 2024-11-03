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
            cloud: bool = False,
            **kwargs
    ):
        default_rate_limiter = RateLimiter(tokens=40, interval=1)
        rate_limiter = kwargs.pop('rate_limiter', default_rate_limiter)

        # Remove 'api_root' from kwargs to prevent conflicts
        kwargs.pop("api_root", None)

        self.cloud = cloud
        api_root = "rest/insight/1.0" if not cloud else None

        super().__init__(
            url=url,
            api_root=api_root,
            rate_limiter=rate_limiter,
            **kwargs
        )

        self.default_headers = {"Accept": "application/json"}

    async def __aenter__(self):
        if self.cloud:
            await self._initialize_cloud()
        else:
            await self._initialize_datacenter()
        return await super().__aenter__()

    async def initialize(self):
        if self.cloud:
            await self._initialize_cloud()

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

    async def _initialize_datacenter(self):
        """
        Initializes the client for Jira Data Center by setting the base URL and API root.
        """
        # Set the base URL to the provided Jira URL
        self.api_url = self.url
        # Set the API root for Data Center
        self.api_root = "rest/insight/1.0"


    async def _get_workspace_id(self):
        """
        Retrieves the workspace ID for Assets Cloud.
        """
        url = self.url_joiner(self.url, "rest/servicedeskapi/assets/workspace")
        response = await self.get(url, absolute=True)
        return response["values"][0]["workspaceId"]

    # Attachments
    async def get_attachments_of_objects(self, object_id):
        """
        Fetches attachment information for a specified object ID.

        Args:
            object_id (str): The ID of the object to retrieve attachments for.

        Returns:
            list: A list of attachment information objects.
        """

        if self.cloud:
            raise NotImplementedError
        url = self.url_joiner(
            self.api_root,
            "attachments/object/{objectId}".format(objectId=object_id),
        )
        return await self.get(url)

    async def upload_attachment_to_object(self, object_id: int, filename: str) -> Dict[str, str]:
        """
        Uploads an attachment to a specified object.

        Args:
            object_id (int): The ID of the object to attach the file to.
            filename (str): The path to the file to be uploaded.

        Returns:
            dict: The response from the API after uploading the attachment.
        """

        if self.cloud:
            raise NotImplementedError
        log.warning("Adding attachment...")
        url = f"rest/insight/1.0/attachments/object/{object_id}"
        async with aiofiles.open(filename, "rb") as attachment:
            files = {"file": await attachment.read()}
            return await self.post(url, headers=self.no_check_headers, files=files)

    async def delete_attachment(self, attachment_id: int) -> Dict[str, str]:
        """
        Deletes an attachment based on the provided attachment ID.

        Args:
            attachment_id (int): The ID of the attachment to be deleted.

        Returns:
            dict: The response from the API after deleting the attachment.
        """

        if self.cloud:
            raise NotImplementedError
        log.warning("Adding attachment...")
        url = "rest/insight/1.0/attachments/{attachmentId}".format(attachmentId=attachment_id)
        return await self.delete(url)

    async def add_comment_to_object(self, comment: str, object_id: int, role: str) -> Dict[str, str]:
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
            raise NotImplementedError
        params = {"comment": comment, "objectId": object_id, "role": role}
        url = "rest/insight/1.0/comment/create"
        return await self.post(url, params=params)

    async def get_comment_of_object(self, object_id):
        """
        Retrieves comments for a specified object ID.

        Args:
            object_id (int): The ID of the object to retrieve comments for.

        Returns:
            list: A list of comments associated with the object.
        """

        if self.cloud:
            raise NotImplementedError
        url = "rest/insight/1.0/comment/object/{objectId}".format(objectId=object_id)
        return await self.get(url)

    async def get_icon_by_id(self, icon_id) -> Dict[str, str]:
        """
        Retrieves information about an icon by its ID.

        Args:
            icon_id (int): The ID of the icon.

        Returns:
            dict: Icon information.
        """

        url = self.url_joiner(self.api_root, "icon/{id}".format(id=icon_id))
        return await self.get(url)

    async def get_all_global_icons(self) -> Dict[str, str]:
        """
        Retrieves information about all global icons.

        Returns:
            list: A list of global icons.
        """

        url = self.url_joiner(self.api_root, "icon/global")
        return await self.get(url)

    async def start_import_configuration(self, import_id: int) -> Dict[str, str]:
        """
        Starts the import process for a given import configuration.

        Args:
            import_id (int): The ID of the import configuration.

        Returns:
            dict: The response from the API after starting the import.
        """

        url = self.url_joiner(
            self.api_root,
            "import/start/{import_id}".format(import_id=import_id),
        )
        return await self.post(url)

    async def reindex_insight(self) -> Dict[str, str]:
        """
        Initiates reindexing of Insight.

        Returns:
            dict: The response from the API after starting the reindexing.
        """

        if self.cloud:
            raise NotImplementedError
        url = self.url_joiner(self.api_root, "index/reindex/start")
        return await self.post(url)

    async def reindex_current_node_insight(self) -> Dict[str, str]:
        """
        Initiates reindexing of the current node in Insight.

        Returns:
            dict: The response from the API after starting the reindexing for the current node.
        """

        if self.cloud:
            raise NotImplementedError
        url = self.url_joiner(self.api_root, "index/reindex/currentnode")
        return await self.post(url)

    async def get_object_schemas(self) -> Dict[str, str]:
        """
        Retrieves information about an object schema based on its ID.

        Returns:
            dict: The details of the specified object schema.
        """

        # Assuming the URL to get object types is similar to the one for getting object schema
        url = self.url_joiner(
            self.api_root,
            f"objectschema/list"
        )
        result = await self.get(url)
        return result


    async def get_object_schema(self, schema_id: int) -> Dict[str, str]:
        """
        Retrieves information about an object schema based on its ID.

        Args:
            schema_id (int): The ID of the object schema.

        Returns:
            dict: The details of the specified object schema.
        """

        # Assuming the URL to get object types is similar to the one for getting object schema
        url = self.url_joiner(
            self.api_root,
            f"objectschema/{schema_id}"
        )
        result = await self.get(url)
        return result


    async def create_object_schema(self, name: str, description: str) -> Dict[str, str]:
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

    async def update_object_schema(self, schema_id: int, name: str, description: str) -> Dict[str, str]:
        """
        Updates an object schema based on the provided schema ID.

        Args:
            schema_id (int): The ID of the object schema to update.
            name (str): The new name for the object schema.
            description (str): The new description for the object schema.

        Returns:
            dict: The response from the API after updating the object schema.
        """

        url = self.url_joiner(self.api_root, "objectschema/{id}".format(id=schema_id))
        body = {"name": name, "description": description}
        return await self.put(url, json=body)

    async def get_object_schema_object_types(self, schema_id: int) -> List[Dict[str, str]]:
        """
        Retrieves all object types for a given object schema.

        Args:
            schema_id (int): The ID of the object schema.

        Returns:
            list: A list of object types for the specified schema.
        """

        # Assuming the URL to get object types is similar to the one for getting object schema
        url = self.url_joiner(
            self.api_root,
            f"objectschema/{schema_id}/objecttypes"
        )
        return await self.get(url)

    async def get_object_schema_object_types_flat(self, schema_id: int) -> List[Dict[str, str]]:
        """
        Retrieves all object types for a given object schema in a flat structure.

        Args:
            schema_id (int): The ID of the object schema.

        Returns:
            list: A flat list of object types for the specified schema.
        """

        # Assuming the URL to get object types is similar to the one for getting object schema
        url = self.url_joiner(
            self.api_root,
            f"objectschema/{schema_id}/objecttypes/flat"
        )
        return await self.get(url)

    async def get_object_schema_object_attributes(self, schema_id,
                                                  only_value_editable=False,
                                                  order_by_name=False,
                                                  query=None,
                                                  include_value_exist=False,
                                                  exclude_parent_attributes=False,
                                                  include_children=False,
                                                  order_by_required=False):
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

        # Construct the URL
        url = self.url_joiner(
            self.api_root,
            f"objectschema/{schema_id}/attributes"
        )

        # Construct the parameters dictionary by filtering out default/None values
        params = {
            'onlyValueEditable': only_value_editable,
            'orderByName': order_by_name,
            'query': query,
            'includeValueExist': include_value_exist,
            'excludeParentAttributes': exclude_parent_attributes,
            'includeChildren': include_children,
            'orderByRequired': order_by_required
        }
        # Remove parameters with default values or None
        params = {k: v for k, v in params.items() if v not in (False, None)}

        return await self.get(url, params=params)

    async def aql_query(
            self,
            ql_query: str = None,
            page: int = 1,
            result_per_page: int = 25,
            include_attributes: bool = True,
            include_attributes_deep: int = 1,
            include_type_attributes: bool = False,
            include_extended_info: bool = False,
            object_schema_id: str = None
    ) -> dict:
        """
        Runs an AQL query and fetches the results from the Insight API.

        Args:
            ql_query (str, optional): The query to determine which objects should be fetched. Defaults to None.
            page (int, optional): The page to fetch when paginating through the response. Defaults to 1.
            result_per_page (int, optional): The number of objects returned per page. Defaults to 25.
            include_attributes (bool, optional): Should object attributes be included in the response. Defaults to True.
            include_attributes_deep (int, optional): How many levels of attributes should be included in the response. Defaults to 1.
            include_type_attributes (bool, optional): Should the response include the object type attribute definition for each attribute. Defaults to False.
            include_extended_info (bool, optional): Should the response include information about open issues and attachments. Defaults to False.
            object_schema_id (str, optional): Limit the scope of objects to find based on this schema. Defaults to None.

        Returns:
            dict: The API response containing the queried objects.
        """

        try:
            return await self.get_objects_by_aql(
                schema_id=int(object_schema_id) if object_schema_id else None,
                object_type_id=int(object_schema_id) if object_schema_id else None,
                aql_query=ql_query,
                page=page,
                results_per_page=result_per_page,
                include_attributes=include_attributes
            )

        except HTTPError as e:
            log.error(f"Error fetching objects: {e}")
            return {}

        finally:
            raise DeprecationWarning("This method is deprecated. Use the get_object_by_aql method instead.")

    async def iql(
            self,
            iql: str,
            object_schema_id: int = None,
            page: int =1,
            order_by_attribute_id: int = None,
            order_asc: bool = True,
            result_per_page: int = 25,
            include_attributes: bool = True,
            include_attributes_deep: int = 1,
            include_type_attributes: bool = False,
            include_extended_info: bool = False,
            extended: Dict[str, str] = None,
    ) -> Dict[str, str]:
        raise DeprecationWarning("This method is deprecated. Use the get_objects_by_aql method instead.")

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
            schema_id (int): The ID of the schema
            object_type_id (int): The ID of the object type
            aql_query (str): The AQL query string
            page (int, optional): The page number (default is 1)
            results_per_page (int, optional): Number of results per page (default is 25)

        Returns:
            dict: The response containing matching objects
        """
        # All parameters go in the query string for GET request
        query = {
            'includeAttributes': True,
        }

        log.debug(f"Query parameters: {query}")

        payload = {
            "objectTypeId": object_type_id,
            "page": page,
            "asc": 1,
            "resultsPerPage": results_per_page,
            "includeAttributes": include_attributes,
            "objectSchemaId": schema_id,
            "qlQuery": aql_query
        }


        result = await self.post(
            "rest/insight/1.0/object/navlist/aql",
            json=payload
        )
        return result


    async def get_object(self, object_id: int) -> Dict[str, str]:
        """
        Retrieves information about a specific object by its ID.

        Args:
            object_id (int): The ID of the object.

        Returns:
            dict: The details of the specified object.
        """

        url = self.url_joiner(self.api_root, "object/{id}".format(id=object_id))
        result = await self.get(url)
        return result

    async def get_object_type_attributes(
            self,
            object_id: int,
            only_value_editable: bool = False,
            order_by_name: bool = False,
            query: str = None,
            include_value_exist: bool = False,
            exclude_parent_attributes: bool = False,
            include_children: bool = True,
            order_by_required: bool = False
    ) -> Dict[str, str]:
        """
        Fetches all object type attributes for a given object type.

        Args:
            object_id (int): The ID of the object type.
            only_value_editable (bool): If True, only includes attributes where only the value is editable. Defaults to False.
            order_by_name (bool): If True, orders the response by name. Defaults to False.
            query (str): Filters attributes that start with the provided query string. Defaults to None.
            include_value_exist (bool): If True, includes only attributes where attribute values exist. Defaults to False.
            exclude_parent_attributes (bool): If True, excludes parent attributes from the response. Defaults to False.
            include_children (bool): If True, includes child attributes in the response. Defaults to True.
            order_by_required (bool): If True, orders the response by the number of required attributes. Defaults to False.

        Returns:
            dict: The result from the API call.
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
            """
            This parameter is the stupidest parameter in the history of parameters. Basically it allows you to filter
            attributes based on the name of the attribute. Essentially pythons .startswith() run on the name key.
            instead of being iql which would have been actually useful.
            """
            params["query"] = query

        url = self.url_joiner(self.api_root, f"objecttype/{object_id}/attributes")
        return await self.get(url, params=params)

    async def update_object(
        self,
        object_id: int,
        object_type_id: int,
        attributes: List[Dict],
        has_avatar: bool = False,
        avatar_uuid: str = "",
    ):
        """
        Updates an object with new data.

        Args:
            object_id (int): The ID of the object to update.
            object_type_id (int): The ID of the object type.
            attributes (dict): A dictionary of attributes to update on the object.
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
        url = self.url_joiner(self.api_root, "object/{id}".format(id=object_id))
        return await self.put(url, data=body)

    async def delete_object(self, object_id: int) -> Dict[str, str]:
        """
        Deletes an object based on its ID.

        Args:
            object_id (int): The ID of the object to delete.

        Returns:
            dict: The response from the API after deleting the object.
        """

        url = self.url_joiner(self.api_root, "object/{id}".format(id=object_id))
        return await self.delete(url)

    async def get_object_attributes(self, object_id: int) -> Dict[str, str]:
        """
        Retrieves attributes of an object.

        Args:
            object_id (int): The ID of the object to retrieve attributes for.

        Returns:
            dict: The object's attributes returned by the API.
        """

        url = self.url_joiner(self.api_root, "object/{id}/attributes".format(id=object_id))
        return await self.get(url)

    async def get_object_history(
            self,
            object_id: int,
            asc: bool = False,
            abbreviate: bool = True
    ) -> Dict[str, str]:
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
        url = self.url_joiner(self.api_root, "object/{id}/history".format(id=object_id))
        return await self.get(url, params=params)

    async def get_object_reference_info(self, object_id: int) -> Dict[str, str]:
        """
        Retrieves reference information for an object.

        Args:
            object_id (int): The ID of the object to retrieve reference information for.

        Returns:
            dict: Reference information for the object, as returned by the API.
        """

        url = self.url_joiner(self.api_root, "object/{id}/referenceinfo".format(id=object_id))
        return await self.get(url)

    async def get_status_types(self, object_schema_id: int = None) -> Dict[str, str]:
        """
        Retrieves status types for a given object schema ID.

        Args:
            object_schema_id (int, optional): The ID of the object schema. If not provided,
                                              it will return all global statuses.

        Returns:
            list: A list of status type objects.
        """
        url = self.url_joiner(self.api_root, "config/statustype")

        params = {}
        if object_schema_id is not None:
            params['objectSchemaId'] = object_schema_id

        result = await self.get(url, params=params)
        return result

    async def create_object(
            self,
            object_type_id: int,
            attributes: List[Dict[str, str]],
            has_avatar: bool = False,
            avatar_uuid: str = ""
    ) -> Dict[str, str]:
        """
        Creates a new object with the specified attributes.

        Args:
            object_type_id (int): The ID of the object type for the new object.
            attributes (List[dict]): A dictionary of attributes for the new object.
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