import asyncio

from aio_insight.aio_insight import AsyncInsight


class PageFetchError(Exception):
    """Exception raised for errors in the page fetching process.

    Attributes:
        message -- explanation of the error
    """

    def __init__(self, message="Failed to fetch a page from the API"):
        self.message = message
        super().__init__(self.message)


class AsyncQueryInsight:
    PAGE_SIZE = 20
    INCLUDE_ATTRIBUTES_DEEP = 2
    INCLUDE_TYPE_ATTRIBUTES = False
    CONCURRENT_REQUESTS = 20

    def __init__(self, url, token, query: str|None, schema_id=None, page_size=None, rate_limiter=None):
        """
        Initializes an instance of AsyncQueryInsight.

        Args:
            url (str): The base URL for the Jira instance.
            token (str): The authentication token for accessing Jira.
            query (str, optional): The query string to execute. Can be None.
            schema_id (int, optional): The ID of the schema to query against. Defaults to None.
            page_size (int, optional): The number of results to return per page. Defaults to PAGE_SIZE.
            rate_limiter (RateLimiter, optional): An optional rate limiter instance.

        Attributes:
            jira (AsyncInsight): An instance of AsyncInsight for API interactions.
            query (str|None): The IQL query string.
            schema_id (int|None): The ID of the Insight object schema.
            page_size (int): Number of results per page.
        """

        self.jira = AsyncInsight(
            url=url,
            token=token,
            cloud=False,
            rate_limiter=rate_limiter
        )
        self.query = query
        self.schema_id = schema_id or None
        self.page_size = page_size or self.PAGE_SIZE

    async def _get_initial_page(self):
        """
        Fetches the initial page of data based on the provided query and schema ID.

        Returns:
            dict: The response from the Jira API for the initial page of data.
        """

        return await self.jira.iql(
            self.query,
            object_schema_id=self.schema_id,
            result_per_page=self.page_size,
            include_attributes_deep=self.INCLUDE_ATTRIBUTES_DEEP,
            include_type_attributes=self.INCLUDE_TYPE_ATTRIBUTES,
            include_extended_info=False,
        )

    async def _schemas(self, page):
        """
        Processes schemas for each attribute in the provided page.

        Args:
            page (dict): A page of results from the Jira API.

        Returns:
            None: The method operates asynchronously to process schemas.
        """

        for attribute in page.get("objectTypeAttributes"):
            reference_object_type_id = attribute.get("referenceObjectTypeId")
            if reference_object_type_id:
                schema_id = attribute.get("referenceObjectType").get("objectSchemaId")
                await self.jira.get_object_schema(schema_id)
                await self.jira.get_object_schema_object_types_flat(schema_id)

    async def fetch_page(self, page_num):
        """
        Fetches a specific page of data based on the provided page number.

        Args:
            page_num (int): The page number to fetch.

        Returns:
            dict: The response from the Jira API for the specified page.
        """

        return await self.jira.iql(
            self.query,
            object_schema_id=self.schema_id,
            page=page_num,
            result_per_page=self.page_size,
            include_attributes_deep=self.INCLUDE_ATTRIBUTES_DEEP,
            include_type_attributes=self.INCLUDE_TYPE_ATTRIBUTES,
            include_extended_info=False,
        )

    async def fetch_pages(self):
        """
        Fetches multiple pages of data asynchronously based on the initial query and schema ID.

        Returns:
            list: A list of pages, each page being a dictionary containing the data for that page.

        Raises:
            ValueError: If initial page lacks required information.
            IOError: If there's a failure in fetching any of the pages.
        """

        # Fetch the initial page.
        initial_page = await self._get_initial_page()

        pages = [initial_page]
        total_count = initial_page.get('totalFilterCount', 0)
        page_object_size = initial_page.get('pageObjectSize', 0)

        if not total_count or not page_object_size:
            # Handle cases where total_count or page_object_size is not available.
            raise ValueError("The initial page is missing required information.")

        # Calculate number of remaining pages.
        start_indices = range(page_object_size + 1, total_count, page_object_size)
        # Semaphore to control the number of concurrent requests
        sem = asyncio.Semaphore(self.CONCURRENT_REQUESTS)

        async def fetch_with_limit(page_num):
            async with sem:  # Ensure only a limited number of requests run at once
                return await self.fetch_page(page_num)

        # Fetch remaining pages asynchronously.
        futures = [
            fetch_with_limit(page_num)
            for page_num, _ in enumerate(start_indices, start=2)
        ]

        rest_of_pages = await asyncio.gather(*futures, return_exceptions=True)

        # Optionally, filter out exceptions and handle them
        # This step can be omitted if you want exceptions to propagate and terminate the gathering
        successful_pages = [page for page in rest_of_pages if not isinstance(page, Exception)]
        failed_pages = [page for page in rest_of_pages if isinstance(page, Exception)]

        if len(failed_pages) > 0:
            raise PageFetchError(f"Failed to fetch {len(failed_pages)} pages from Insight!")

        pages.extend(successful_pages)

        return pages
