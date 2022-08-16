import json

import httpx
import pytest

from mocket import async_mocketize
from mocket.mockhttp import Entry


@pytest.mark.asyncio
@async_mocketize
async def test_httpx():
    url = "https://example.org/"
    data = {"message": "Hello"}

    Entry.single_register(
        Entry.GET,
        url,
        body=json.dumps(data),
        headers={"content-type": "application/json"},
    )

    async with httpx.AsyncClient() as client:
        response = await client.get(url)

        assert response.json() == data
