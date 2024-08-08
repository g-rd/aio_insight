import logging

import aiofiles

from aio_insight.aio_api_client import RateLimitedAsyncAtlassianRestAPI

log = logging.getLogger(__name__)


class AsyncInsight(RateLimitedAsyncAtlassianRestAPI):
    """
    A wrapper class for asynchronous interactions with the Insight for Jira API. This class provides methods to
    handle various operations for both standard and cloud-based Insight instances, inheriting from
    RateLimitedAsyncAtlassianRestAPI for rate-limited API access.

    Attributes:
        cloud (bool): Indicates if the instance is for Insight Cloud.
        api_root (str): The root URL for API requests.
        default_headers (dict): Default headers used for API requests.
    """

    def __init__(self, *args, **kwargs):
        """
        Initializes the AsyncInsight class, setting up the API root and preparing for either cloud or non-cloud
        interactions based on provided arguments.

        Args:
            *args: Variable length argument list, passed to the superclass constructor.
            **kwargs: Arbitrary keyword arguments. 'cloud' key indicates cloud-based operation.
        """

        kwargs["api_root"] = "rest/insight/1.0"
        self.cloud = kwargs.pop("cloud", False)

        # Pass connection pooling parameters
        max_connections = kwargs.pop("max_connections", 100)
        max_keepalive_connections = kwargs.pop("max_keepalive_connections", 20)
        keepalive_expiry = kwargs.pop("keepalive_expiry", 60)

        super().__init__(
            *args,
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry,
            **kwargs
        )

    async def initialize(self):
        if self.cloud:
            await self.__cloud_init()

    async def __cloud_init(self):
        """
        Initializes settings specific to Insight Cloud by setting up the API root URL and default headers for
        cloud-based operations.
        """

        # retrieve cloud workspace id and generate the api_root

        workspace_id = await self.__get_workspace_id()
        self.api_root = f"/jsm/insight/workspace/{workspace_id}/v1/"
        self.url = "https://api.atlassian.com"
        self.default_headers = {"Accept": "application/json"}

    async def __get_workspace_id(self):
        """
        Retrieves the workspace ID for Insight Cloud, used in constructing API endpoints.

        Returns:
            str: The workspace ID.
        """

        result = await self.get(
            "rest/servicedeskapi/insight/workspace",
            headers=self.default_headers,
        )
        return result["values"][0]["workspaceId"]

    async def _get_insight_workspace_ids(self):
        """
        Retrieves a list of all workspace IDs for Insight Cloud.

        Returns:
            List[str]: A list of workspace IDs.
        """

        result = await self.get(
            "rest/servicedeskapi/insight/workspace",
            headers=self.experimental_headers,
        )
        return [i["workspaceId"] for i in result["values"]]

    async def _get_insight_workspace_id(self):
        """
        Retrieves the first workspace ID for Insight Cloud.

        Returns:
            str: The first workspace ID.
        """

        return next(iter(await self._get_insight_workspace_ids()))

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

    async def upload_attachment_to_object(self, object_id, filename):
        """
        Uploads an attachment to a specified object.

        Args:
            object_id (str): The ID of the object to attach the file to.
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

    async def delete_attachment(self, attachment_id):
        """
        Deletes an attachment based on the provided attachment ID.

        Args:
            attachment_id (str): The ID of the attachment to be deleted.

        Returns:
            dict: The response from the API after deleting the attachment.
        """

        if self.cloud:
            raise NotImplementedError
        log.warning("Adding attachment...")
        url = "rest/insight/1.0/attachments/{attachmentId}".format(attachmentId=attachment_id)
        return await self.delete(url)

    async def add_comment_to_object(self, comment, object_id, role):
        """
        Adds a comment to a specified object.

        Args:
            comment (str): The comment text to be added.
            object_id (str): The ID of the object to add the comment to.
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
            object_id (str): The ID of the object to retrieve comments for.

        Returns:
            list: A list of comments associated with the object.
        """

        if self.cloud:
            raise NotImplementedError
        url = "rest/insight/1.0/comment/object/{objectId}".format(objectId=object_id)
        return await self.get(url)

    async def get_icon_by_id(self, icon_id):
        """
        Retrieves information about an icon by its ID.

        Args:
            icon_id (str): The ID of the icon.

        Returns:
            dict: Icon information.
        """

        url = self.url_joiner(self.api_root, "icon/{id}".format(id=icon_id))
        return await self.get(url)

    async def get_all_global_icons(self):
        """
        Retrieves information about all global icons.

        Returns:
            list: A list of global icons.
        """

        url = self.url_joiner(self.api_root, "icon/global")
        return await self.get(url)

    async def start_import_configuration(self, import_id):
        """
        Starts the import process for a given import configuration.

        Args:
            import_id (str): The ID of the import configuration.

        Returns:
            dict: The response from the API after starting the import.
        """

        url = self.url_joiner(
            self.api_root,
            "import/start/{import_id}".format(import_id=import_id),
        )
        return await self.post(url)

    async def reindex_insight(self):
        """
        Initiates reindexing of Insight.

        Returns:
            dict: The response from the API after starting the reindexing.
        """

        if self.cloud:
            raise NotImplementedError
        url = self.url_joiner(self.api_root, "index/reindex/start")
        return await self.post(url)

    async def reindex_current_node_insight(self):
        """
        Initiates reindexing of the current node in Insight.

        Returns:
            dict: The response from the API after starting the reindexing for the current node.
        """

        if self.cloud:
            raise NotImplementedError
        url = self.url_joiner(self.api_root, "index/reindex/currentnode")
        return await self.post(url)

    async def get_object_schema(self, schema_id):
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
        return await self.get(url)

    async def get_object_schema_object_types(self, schema_id):
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

    async def get_object_schema_object_types_flat(self, schema_id):
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

    async def iql(
            self,
            iql,
            object_schema_id=None,
            page=1,
            order_by_attribute_id=None,
            order_asc=True,
            result_per_page=25,
            include_attributes=True,
            include_attributes_deep=1,
            include_type_attributes=False,
            include_extended_info=False,
            extended=None,
    ):
        """
        Executes an Insight Query Language (IQL) query to fetch objects.

        Args:
            iql (str): The IQL query.
            object_schema_id (int, optional): The schema ID to limit the scope of objects. Defaults to None.
            page (int, optional): The page number for pagination. Defaults to 1.
            order_by_attribute_id (int, optional): The attribute ID for ordering results. Defaults to None.
            order_asc (bool, optional): If True, sorts results in ascending order. Defaults to True.
            result_per_page (int, optional): The number of results per page. Defaults to 25.
            include_attributes (bool, optional): If True, includes object attributes in the response. Defaults to True.
            include_attributes_deep (int, optional): The depth of attributes to include. Defaults to 1.
            include_type_attributes (bool, optional): If True, includes the object type attribute definition. Defaults to False.
            include_extended_info (bool, optional): If True, includes information about open issues and attachments. Defaults to False.
            extended (dict, optional): Additional parameters for extended information. Defaults to None.

        Returns:
            dict: The result of the IQL query.
        """

        params = {
            "iql": iql,
            "page": page,
            "resultPerPage": result_per_page,
            "includeAttributes": include_attributes,
            "includeAttributesDeep": include_attributes_deep,
            "includeTypeAttributes": include_type_attributes,
            "includeExtendedInfo": include_extended_info,
        }

        # Add deprecated parameters if they're provided
        if object_schema_id:
            params["objectSchemaId"] = object_schema_id
        if order_by_attribute_id:
            params["orderByAttributeId"] = order_by_attribute_id
        if order_asc is not None:
            params["orderAsc"] = order_asc
        if extended is not None:
            params["extended"] = extended

        url = self.url_joiner(self.api_root, "iql/objects")
        return await self.get(url, params=params)

    async def get_objects_by_aql(self, schema_id, object_type_id, aql_query, page=1, asc=1, results_per_page=25):
        """
        Retrieves a list of objects based on an AQL query.

        Args:

            ql_query (str): The AQL query.

        Returns:
            dict: The response from the API.
        """

        url = self.url_joiner(self.api_root, "/object/navlist/aql")
        body = {
            "objectTypeId": object_type_id,
            "attributesToDisplay": {
                "attributesToDisplayIds": []
            },
            "page": page,
            "asc": asc,
            "resultsPerPage": results_per_page,
            "includeAttributes": False,
            "objectSchemaId": schema_id,
            "qlQuery": aql_query
        }
        log.debug(f"Sending AQL query to URL: {url}")
        return await self.post(url, json=body)

    async def get_object(self, object_id):
        """
        Retrieves information about a specific object by its ID.

        Args:
            object_id (int): The ID of the object.

        Returns:
            dict: The details of the specified object.
        """

        url = self.url_joiner(self.api_root, "object/{id}".format(id=object_id))
        return await self.get(url)

    async def get_object_type_attributes(
            self,
            object_id,
            only_value_editable=False,
            order_by_name=False,
            query=None,
            include_value_exist=False,
            exclude_parent_attributes=False,
            include_children=True,
            order_by_required=False
    ):
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
        object_id,
        object_type_id,
        attributes,
        has_avatar=False,
        avatar_uuid="",
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

    async def delete_object(self, object_id):
        """
        Deletes an object based on its ID.

        Args:
            object_id (int): The ID of the object to delete.

        Returns:
            dict: The response from the API after deleting the object.
        """

        url = self.url_joiner(self.api_root, "object/{id}".format(id=object_id))
        return await self.delete(url)

    async def get_object_attributes(self, object_id):
        """
        Retrieves attributes of an object.

        Args:
            object_id (int): The ID of the object to retrieve attributes for.

        Returns:
            dict: The object's attributes returned by the API.
        """

        url = self.url_joiner(self.api_root, "object/{id}/attributes".format(id=object_id))
        return await self.get(url)

    async def get_object_history(self, object_id, asc=False, abbreviate=True):
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

    async def get_object_reference_info(self, object_id):
        """
        Retrieves reference information for an object.

        Args:
            object_id (int): The ID of the object to retrieve reference information for.

        Returns:
            dict: Reference information for the object, as returned by the API.
        """

        url = self.url_joiner(self.api_root, "object/{id}/referenceinfo".format(id=object_id))
        return await self.get(url)

    async def get_status_types(self, object_schema_id=None):
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

        return await self.get(url, params=params)

    async def create_object(self, object_type_id, attributes, has_avatar=False, avatar_uuid=""):
        """
        Creates a new object with the specified attributes.

        Args:
            object_type_id (int): The ID of the object type for the new object.
            attributes (dict): A dictionary of attributes for the new object.
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