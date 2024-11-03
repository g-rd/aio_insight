import asyncio
import time
import logging
from json import dumps
from typing import Optional, Dict, Tuple, Any, Union, FrozenSet, List

import httpx
from httpx import Response, AsyncClient, Limits, HTTPError

from six.moves.urllib.parse import urlencode

CacheKeyType = Tuple[str, FrozenSet[Tuple[str, Union[str, Tuple[str, str]]]], FrozenSet[Tuple[str, Union[str, Tuple[str, str]]]]]

# Configure logging
log = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter class to control the frequency of API requests.

    Attributes:
        tokens (int): Maximum number of requests per interval.
        interval (float): Time interval in seconds.
        next_available (float): Timestamp for when the next request is allowed.
        lock (asyncio.Lock): Async lock to ensure thread-safe operations.
    """
    def __init__(self, tokens: int, interval: float):
        self.tokens = tokens
        self.interval = interval
        self.next_available = time.monotonic()
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Acquire permission to make a request, waiting if necessary."""
        async with self.lock:
            now = time.monotonic()
            if now < self.next_available:
                await asyncio.sleep(self.next_available - now)
            self.next_available = max(now, self.next_available) + self.interval / self.tokens

    async def __aenter__(self):
        await self.acquire()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass

class AsyncAtlasRestAPI:
    """
    Asynchronous REST API client for interacting with a RESTful Atlas API.

    Attributes:
        url (str): The base URL for the API.
        username (Optional[str]): Username for basic authentication.
        password (Optional[str]): Password for basic authentication.
        timeout (int): Timeout for API requests in seconds.
        api_root (str): Root path for API endpoints.
        api_version (str): Version of the API to use.
        verify_ssl (bool): Whether to verify SSL certificates.
        session (AsyncClient): HTTPX session for making async requests.
    """
    default_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    def __init__(
            self,
            url,
            username=None,
            password=None,
            timeout=75,
            api_root="rest/api",
            api_version="latest",
            verify_ssl=True,
            session: Optional[AsyncClient] = None,
            oauth=None,
            oauth2=None,
            cookies=None,
            advanced_mode=False,
            kerberos=None,
            proxies=None,
            token=None,
            cert=None,
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=60,
    ):
        self.url = url
        self.username = username
        self.password = password
        self.timeout = int(timeout)
        self.verify_ssl = verify_ssl
        self.api_root = api_root
        self.api_version = api_version
        self.cookies = cookies
        self.advanced_mode = advanced_mode
        self.proxies = proxies
        self.cert = cert

        # Cache and concurrency management
        self.cache: Dict[Tuple[str, FrozenSet[Tuple[str, Union[str, Tuple[str, str]]]], FrozenSet[Tuple[str, Union[str, Tuple[str, str]]]]], Tuple[Any, float]] = {}
        self.cache_expiry_time = 300  # Cache expiration time in seconds (5 minutes)
        self.cache_lock = asyncio.Lock()  # Lock for concurrency control

        limits = Limits(max_connections=max_connections, max_keepalive_connections=max_keepalive_connections,
                        keepalive_expiry=keepalive_expiry)

        if session is None:
            self._session = AsyncClient(limits=limits, timeout=self.timeout, verify=self.verify_ssl)
        else:
            self._session = session

        if username and password:
            self._create_basic_session(username, password)
        elif token is not None:
            self._create_token_session(token)
        elif oauth is not None:
            self._create_oauth_session(oauth)
        elif oauth2 is not None:
            self._create_oauth2_session(oauth2)
        elif kerberos is not None:
            self._create_kerberos_session(kerberos)
        elif cookies is not None:
            self._session.cookies.update(cookies)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    def _create_basic_session(self, username, password):
        """Set up basic authentication for the session."""
        self._session.auth = (username, password)

    def _create_token_session(self, token):
        """Add Bearer token authentication to the session headers."""
        self._update_header("Authorization", f"Bearer {token}")

    async def close(self):
        """Close the HTTPX session and clear the cache."""
        # Clear the cache on closing the session
        async with self.cache_lock:
            self.cache.clear()
        await self._session.aclose()

    def _update_header(self, key, value):
        """Update or add a header to the session."""
        self._session.headers[key] = value

    @staticmethod
    async def _response_handler(response):
        """
        Parse JSON response, handling errors and missing content.

        Args:
            response (Response): HTTPX response object.

        Returns:
            Parsed JSON or None if no content.
        """
        try:
            return response.json()
        except ValueError:
            log.debug("Received response with no content")
            return None
        except Exception as e:
            log.error(e)
            return None

    def log_curl_debug(self, method, url, data=None, headers=None, level=logging.DEBUG):
        """
        Log the equivalent curl command for debugging purposes.

        Args:
            method (str): HTTP method.
            url (str): URL of the request.
            data (Any): Data sent in the request.
            headers (Optional[Dict[str, str]]): Request headers.
            level (int): Logging level.
        """
        headers = headers or self.default_headers
        message = "curl --silent -X {method} -H {headers} {data} '{url}'".format(
            method=method,
            headers=" -H ".join(["'{0}: {1}'".format(key, value) for key, value in headers.items()]),
            data="" if not data else "--data '{0}'".format(dumps(data)),
            url=url,
        )
        log.log(level=level, msg=message)

    def resource_url(self, resource, api_root=None, api_version=None):
        """
        Construct the URL for a resource endpoint.

        Args:
            resource (str): Resource endpoint.
            api_root (Optional[str]): API root path.
            api_version (Optional[str]): API version.

        Returns:
            str: Full URL to the resource.
        """
        if api_root is None:
            api_root = self.api_root
        if api_version is None:
            api_version = self.api_version
        return "/".join(str(s).strip("/") for s in [api_root, api_version, resource] if s is not None)

    @staticmethod
    def url_joiner(url, *paths, trailing=None):
        """
        Join URL with multiple paths.

        Args:
            url (str): Base URL.
            *paths: Paths to append.
            trailing (Optional[str]): Whether to add trailing slash.

        Returns:
            str: Constructed URL.
        """
        url_link = "/".join(str(s).strip("/") for s in [url, *paths] if s is not None)
        if trailing:
            url_link += "/"
        return url_link

    def raise_for_status(self, response: Response):
        """
        Raise HTTP errors with custom error message handling.

        Args:
            response (Response): HTTPX response object.
        """
        if response.status_code == 401 and response.headers.get("Content-Type") != "application/json;charset=UTF-8":
            raise HTTPError("Unauthorized (401)", response=response)

        if 400 <= response.status_code < 600:
            try:
                j = response.json()
                if self.url == "https://api.atlassian.com":
                    error_msg = "\n".join([str(k) + ": " + str(v) for k, v in j.items()])
                else:
                    error_msg_list = j.get("errorMessages", list())
                    errors = j.get("errors", dict())
                    if isinstance(errors, dict):
                        error_msg_list.append(errors.get("message", ""))
                    elif isinstance(errors, list):
                        error_msg_list.extend([v.get("message", "") if isinstance(v, dict) else v for v in errors])
                    error_msg = "\n".join(error_msg_list)
            except Exception as e:
                log.error(e)
                response.raise_for_status()
            else:
                log.error(response.content)  # Log the error message
                raise HTTPError(error_msg)  # Include error_msg in the exception

    async def request(
            self,
            method="GET",
            path="/",
            data=None,
            json=None,
            flags=None,
            params=None,
            headers=None,
            files=None,
            trailing=None,
            absolute=False,
            advanced_mode=False,
    ):
        """
        Perform an HTTP request.

        Args:
            method (str): HTTP method.
            path (str): Endpoint path.
            data (Optional[Any]): Data to send.
            json (Optional[Dict]): JSON data to send.
            flags (Optional[Dict]): URL flags.
            params (Optional[Dict]): URL parameters.
            headers (Optional[Dict]): Request headers.
            files (Optional[Any]): Files to upload.
            trailing (Optional[str]): Add trailing slash if specified.
            absolute (bool): If true, use absolute URL.
            advanced_mode (bool): Enable advanced mode.

        Returns:
            Response or parsed response content.
        """
        # Determine the base URL
        base_url = None if absolute else (self.api_url if hasattr(self, 'api_url') and self.api_url else self.url)

        # Construct the URL
        url = self.url_joiner(base_url, path, trailing)
        params_already_in_url = "?" in url
        if params or flags:
            url += "&" if params_already_in_url else "?"
        if params:
            url += urlencode(params or {})
        if flags:
            url += ("&" if params or params_already_in_url else "") + "&".join(flags or [])

        if files is None:
            data = dumps(data) if data is not None else None

        headers = headers or self.default_headers

        try:
            # Make the HTTP request using the AsyncClient
            response = await self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json,  # Pass json directly to the request method
                files=files,
            )
            response.encoding = "utf-8"

            log.debug("HTTP: %s %s -> %s %s", method, path, response.status_code, response.content)
            log.debug("HTTP: Response text -> %s", response.text)

            if self.advanced_mode or advanced_mode:
                return response

            self.raise_for_status(response)
            return response

        except httpx.RequestError as exc:
            log.error(f"An error occurred while requesting {exc.request.url!r}.")
            raise
        except httpx.HTTPStatusError as exc:
            log.error(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
            raise

    async def get(
            self,
            path: str,
            data: Optional[Dict[str, Any]] = None,
            flags: Optional[Dict[str, Any]] = None,
            params: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, str]] = None,
            not_json_response: bool = False,
            trailing: Optional[str] = None,
            absolute: bool = False,
            advanced_mode: bool = False,
            use_cache: bool = True
    ) -> Any:
        """
        Perform an HTTP GET request with optional caching.

        Args:
            path (str): API endpoint path.
            data (Optional[Dict[str, Any]]): Data to include in the request.
            flags (Optional[Dict[str, Any]]): URL flags for additional options.
            params (Optional[Dict[str, Any]]): URL parameters.
            headers (Optional[Dict[str, str]]): Headers to include in the request.
            not_json_response (bool): If True, return response content as bytes.
            trailing (Optional[str]): Adds a trailing slash if specified.
            absolute (bool): If True, constructs an absolute URL.
            advanced_mode (bool): If True, returns raw Response object.
            use_cache (bool): If True, caches the response.

        Returns:
            Any: Parsed JSON response or raw response content.
        """

        # Create a unique cache key based on the path and parameters
        param_set = frozenset(
            (k, v) if isinstance(v, (str, int, float, bool)) else (
            k, tuple(v) if isinstance(v, (list, tuple)) else str(v))
            for k, v in (params or {}).items()
        )
        cache_key: CacheKeyType = (path, param_set, param_set)

        # Check if a cached response is available and valid
        if use_cache and cache_key in self.cache:
            cached_response, timestamp = self.cache[cache_key]
            if time.monotonic() - timestamp < self.cache_expiry_time:
                log.info("Returning cached response for %s", path)
                return cached_response

        # Make the HTTP GET request if no valid cache is available
        response = await self.request(
            "GET",
            path=path,
            flags=flags,
            params=params,
            data=data,
            headers=headers,
            trailing=trailing,
            absolute=absolute,
            advanced_mode=advanced_mode,
        )

        # Return the parsed or raw response based on flags
        if self.advanced_mode or advanced_mode:
            return response

        if not_json_response:
            return response.content

        if not response.text:
            return None

        try:
            json_response = response.json()
            if use_cache:
                # Cache the JSON response
                self.cache[cache_key] = (json_response, time.monotonic())
            return json_response
        except Exception as e:
            log.error("Error parsing JSON response: %s", str(e))
            return response.text

    async def post(
            self,
            path,
            data=None,
            json=None,
            headers=None,
            files=None,
            params=None,
            trailing=None,
            absolute=False,
            advanced_mode=False,
    ):
        """
        Perform an HTTP POST request.

        Args:
            path (str): API endpoint path.
            data (Optional[Dict[str, Any]]): Data to include in the request body.
            json (Optional[Dict[str, Any]]): JSON data to include in the request body.
            headers (Optional[Dict[str, str]]): Headers to include in the request.
            files (Optional[Dict[str, Any]]): Files to upload.
            params (Optional[Dict[str, Any]]): URL parameters.
            trailing (Optional[str]): Adds a trailing slash if specified.
            absolute (bool): If True, constructs an absolute URL.
            advanced_mode (bool): If True, returns raw Response object.

        Returns:
            Any: Parsed JSON response or raw response content.
        """
        response = await self.request(
            "POST",
            path=path,
            data=data,
            json=json,
            headers=headers,
            files=files,
            params=params,
            trailing=trailing,
            absolute=absolute,
            advanced_mode=advanced_mode,
        )
        if self.advanced_mode or advanced_mode:
            return response
        return await self._response_handler(response)

    async def put(
            self,
            path,
            data=None,
            json=None,
            headers=None,
            files=None,
            trailing=None,
            params=None,
            absolute=False,
            advanced_mode=False,
    ):
        """
        Perform an HTTP PUT request.

        Args:
            path (str): API endpoint path.
            data (Optional[Dict[str, Any]]): Data to include in the request body.
            json (Optional[Dict[str, Any]]): JSON data to include in the request body.
            headers (Optional[Dict[str, str]]): Headers to include in the request.
            files (Optional[Dict[str, Any]]): Files to upload.
            params (Optional[Dict[str, Any]]): URL parameters.
            trailing (Optional[str]): Adds a trailing slash if specified.
            absolute (bool): If True, constructs an absolute URL.
            advanced_mode (bool): If True, returns raw Response object.

        Returns:
            Any: Parsed JSON response or raw response content.
        """
        response = await self.request(
            "PUT",
            path=path,
            data=data,
            json=json,
            headers=headers,
            files=files,
            params=params,
            trailing=trailing,
            absolute=absolute,
            advanced_mode=advanced_mode,
        )
        if self.advanced_mode or advanced_mode:
            return response
        return await self._response_handler(response)

    async def patch(
            self,
            path,
            data=None,
            headers=None,
            files=None,
            trailing=None,
            params=None,
            absolute=False,
            advanced_mode=False,
    ):
        """
        Perform an HTTP PATCH request.

        Args:
            path (str): API endpoint path.
            data (Optional[Dict[str, Any]]): Data to include in the request body.
            headers (Optional[Dict[str, str]]): Headers to include in the request.
            files (Optional[Dict[str, Any]]): Files to upload.
            params (Optional[Dict[str, Any]]): URL parameters.
            trailing (Optional[str]): Adds a trailing slash if specified.
            absolute (bool): If True, constructs an absolute URL.
            advanced_mode (bool): If True, returns raw Response object.

        Returns:
            Any: Parsed JSON response or raw response content.
        """
        response = await self.request(
            "PATCH",
            path=path,
            data=data,
            headers=headers,
            files=files,
            params=params,
            trailing=trailing,
            absolute=absolute,
            advanced_mode=advanced_mode,
        )
        if self.advanced_mode or advanced_mode:
            return response
        return await self._response_handler(response)

    async def delete(
            self,
            path,
            data=None,
            headers=None,
            params=None,
            trailing=None,
            absolute=False,
            advanced_mode=False,
    ):
        """
        Perform an HTTP DELETE request.

        Args:
            path (str): API endpoint path.
            data (Optional[Dict[str, Any]]): Data to include in the request body.
            headers (Optional[Dict[str, str]]): Headers to include in the request.
            params (Optional[Dict[str, Any]]): URL parameters.
            trailing (Optional[str]): Adds a trailing slash if specified.
            absolute (bool): If True, constructs an absolute URL.
            advanced_mode (bool): If True, returns raw Response object.

        Returns:
            Any: Parsed JSON response or raw response content.
        """
        response = await self.request(
            "DELETE",
            path=path,
            data=data,
            headers=headers,
            params=params,
            trailing=trailing,
            absolute=absolute,
            advanced_mode=advanced_mode,
        )
        if self.advanced_mode or advanced_mode:
            return response
        return await self._response_handler(response)

    @property
    def session(self):
        """
        Return the current HTTP session.

        Returns:
            AsyncClient: The current HTTPX session instance.
        """
        return self._session


class RateLimitedAsyncAtlassianRestAPI(AsyncAtlasRestAPI):
    """
    Rate-limited extension of AsyncAtlasRestAPI.

    Attributes:
        rate_limiter (RateLimiter): Rate limiter instance to control request frequency.
    """
    def __init__(self, rate_limiter=None, *args, **kwargs):
        """
        Initialize the rate-limited API client.

        Args:
            rate_limiter (RateLimiter): Optional rate limiter instance.
            *args: Additional positional arguments for the parent class.
            **kwargs: Additional keyword arguments for the parent class.
        """
        super().__init__(*args, **kwargs)
        self.rate_limiter = rate_limiter

    async def request(self, *args, **kwargs):
        """
        Perform an HTTP request with rate limiting if configured.

        Args:
            *args: Positional arguments for the request.
            **kwargs: Keyword arguments for the request.

        Returns:
            Any: JSON or raw response content.
        """
        if self.rate_limiter:
            async with self.rate_limiter:
                return await super().request(*args, **kwargs)
        else:
            return await super().request(*args, **kwargs)
