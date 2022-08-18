import json

import httpx
import pytest

from mocket import Mocketizer, async_mocketize
from mocket.mockhttp import Entry


@pytest.mark.asyncio
@async_mocketize
async def test_httpx_decorator():
    url = "https://bar.foo/"
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


@pytest.fixture
def httpx_client() -> httpx.AsyncClient:
    with Mocketizer():
        yield httpx.AsyncClient()


@pytest.mark.asyncio
async def test_httpx_fixture(httpx_client):
    url = "https://foo.bar/"
    data = {"message": "Hello"}

    Entry.single_register(
        Entry.GET,
        url,
        body=json.dumps(data),
        headers={"content-type": "application/json"},
    )

    async with httpx_client as client:
        response = await client.get(url)

        assert response.json() == data
