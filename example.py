import asyncio
import logging

from aio_insight.aio_insight import AsyncInsight
from creds import assets_token, assets_url, \
    assets_username

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def validate_token(token: str) -> bool:
    """Validate if the token is not empty"""
    return bool(token and token.strip())


async def use_aio_insight():
    if not await validate_token(assets_token):
        logger.error("Invalid token")
        return

    async with AsyncInsight(
            url=assets_url,  # Should be https://your-domain.atlassian.net
            username=assets_username,
            password=assets_token,
            verify_ssl=True,
            cloud=True
    ) as session:
        schemas = await session.get_object_schemas()
        print(f"Schemas: {schemas}")


if __name__ == "__main__":
    asyncio.run(use_aio_insight())