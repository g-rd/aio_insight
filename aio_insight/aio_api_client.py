import asyncio
import time
import logging
from json import dumps
from typing import Optional, Dict, Tuple, Any, Union, FrozenSet

import httpx
from httpx import Response, AsyncClient, Limits, HTTPError

from six.moves.urllib.parse import urlencode

# Configure logging
log = logging.getLogger(__name__)


class RateLimiter:
    def __init__(self, tokens, interval):
        self.tokens = tokens
        self.capacity = tokens
        self.interval = interval
        self.last_check = time.monotonic()

    async def get_token(self):
        current_time = time.monotonic()
        time_elapsed = current_time - self.last_check

        self.tokens += time_elapsed * (self.capacity / self.interval)
        self.tokens = min(self.tokens, self.capacity)

        if self.tokens < 1:
            sleep_time = (1 - self.tokens) * (self.interval / self.capacity)
            await asyncio.sleep(sleep_time)
            self.tokens -= 1
        else:
            self.tokens -= 1

        self.last_check = time.monotonic()


class AsyncAtlasRestAPI:
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
            cloud=False,
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
        self.cloud = cloud
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
        self._session.auth = (username, password)

    def _create_token_session(self, token):
        self._update_header("Authorization", f"Bearer {token}")

    async def close(self):
        # Clear the cache on closing the session
        async with self.cache_lock:
            self.cache.clear()
        await self._session.aclose()

    def _update_header(self, key, value):
        self._session.headers[key] = value

    @staticmethod
    async def _response_handler(response):
        try:
            return response.json()
        except ValueError:
            log.debug("Received response with no content")
            return None
        except Exception as e:
            log.error(e)
            return None

    def log_curl_debug(self, method, url, data=None, headers=None, level=logging.DEBUG):
        headers = headers or self.default_headers
        message = "curl --silent -X {method} -H {headers} {data} '{url}'".format(
            method=method,
            headers=" -H ".join(["'{0}: {1}'".format(key, value) for key, value in headers.items()]),
            data="" if not data else "--data '{0}'".format(dumps(data)),
            url=url,
        )
        log.log(level=level, msg=message)

    def resource_url(self, resource, api_root=None, api_version=None):
        if api_root is None:
            api_root = self.api_root
        if api_version is None:
            api_version = self.api_version
        return "/".join(str(s).strip("/") for s in [api_root, api_version, resource] if s is not None)

    @staticmethod
    def url_joiner(url, path, trailing=None):
        url_link = "/".join(str(s).strip("/") for s in [url, path] if s is not None)
        if trailing:
            url_link += "/"
        return url_link

    def raise_for_status(self, response: Response):
        if response.status_code == 401 and response.headers.get("Content-Type") != "application/json;charset=UTF-8":
            raise HTTPError("Unauthorized (401)", response=response)

        if 400 <= response.status_code < 600:
            try:
                j = response.json()
                if self.url == "https://api.atlassian.com":
                    error_msg = "\n".join([k + ": " + v for k, v in j.items()])
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
        # Construct the URL
        url = self.url_joiner(None if absolute else self.url, path, trailing)
        params_already_in_url = "?" in url
        if params or flags:
            url += "&" if params_already_in_url else "?"
        if params:
            url += urlencode(params or {})
        if flags:
            url += ("&" if params or params_already_in_url else "") + "&".join(flags or [])

        if files is None:
            data = dumps(data) if data is not None else None
            json_dump = dumps(json) if json is not None else None
        else:
            json_dump = None

        # self.log_curl_debug(
        #     method=method,
        #     url=url,
        #     headers=headers,
        #     data=data if data else json_dump,
        # )

        headers = headers or self.default_headers

        try:
            # Make the HTTP request using the AsyncClient
            response = await self._session.request(
                method=method,
                url=url,
                headers=headers,
                data=data,
                json=json,
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
            path,
            data=None,
            flags=None,
            params=None,
            headers=None,
            not_json_response=None,
            trailing=None,
            absolute=False,
            advanced_mode=False,
            use_cache=True
    ):
        # Create a unique cache key based on the path and parameters
        cache_key = (path, frozenset(params.items()) if params else None)

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
        if self.advanced_mode or advanced_mode:
            return response
        if not_json_response:
            return response.content
        else:
            if not response.text:
                return None
            try:
                # Parse the JSON response
                json_response = response.json()
                if use_cache:
                    # Cache the JSON response
                    self.cache[cache_key] = (json_response, time.monotonic())
                return json_response
            except Exception as e:
                log.error(e)
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
            headers=None,
            files=None,
            trailing=None,
            params=None,
            absolute=False,
            advanced_mode=False,
    ):
        response = await self.request(
            "PUT",
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
        """Providing access to the restricted field"""
        return self._session


class RateLimitedAsyncAtlassianRestAPI(AsyncAtlasRestAPI):
    def __init__(self, rate_limiter=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rate_limiter = rate_limiter

    async def request(self, *args, **kwargs):
        if self.rate_limiter:
            await self.rate_limiter.get_token()
        return await super().request(*args, **kwargs)

