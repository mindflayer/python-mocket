import json

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mocket import Mocketizer, async_mocketize, mocketize
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


def create_app() -> FastAPI:
    app = FastAPI()

    @app.get("/")
    async def read_main() -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.get("https://example.org/")
            return r.json()

    return app


@mocketize
def test_call_from_fastapi() -> None:
    app = create_app()
    client = TestClient(app)

    Entry.single_register(Entry.GET, "https://example.org/", body='{"id": 1}')

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"id": 1}
