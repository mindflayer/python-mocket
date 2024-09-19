import datetime
import json

import httpx
import pytest
from asgiref.sync import async_to_sync
from fastapi import FastAPI
from fastapi.testclient import TestClient

from mocket import Mocket, Mocketizer, async_mocketize, mocketize
from mocket.mockhttp import Entry
from mocket.plugins.httpretty import httprettified, httpretty


@mocketize
@pytest.mark.parametrize("url", ("http://httpbin.org/ip", "https://httpbin.org/ip"))
def test_body(url):
    body = "asd" * 100
    Entry.single_register(Entry.GET, url, body=body, status=404)
    Entry.single_register(Entry.POST, url, body=body * 2, status=201)

    @async_to_sync
    async def perform_async_transactions():
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            assert response.status_code == 404
            assert response.text == body

            response = await client.post(url, data=body * 6)
            assert response.status_code == 201
            assert response.text == body * 2

            assert Mocket.last_request().method == "POST"
            assert Mocket.last_request().body == body * 6

    perform_async_transactions()
    assert len(Mocket.request_list()) == 2


@httprettified
def test_httprettish_session():
    url = "https://httpbin.org/ip"

    expected_response = {"origin": "127.0.0.2"}

    httpretty.register_uri(
        httpretty.GET,
        url,
        body=json.dumps(expected_response),
    )

    @async_to_sync
    async def perform_async_transactions():
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            assert response.status_code == 200
            assert response.json() == expected_response

    perform_async_transactions()
    assert len(httpretty.latest_requests) == 1


@mocketize(strict_mode=True)
def test_sync_case():
    test_uri = "https://abc.de/testdata/"
    base_timestamp = int(datetime.datetime.now().timestamp())
    response = [
        {"timestamp": base_timestamp + i, "value": 1337 + 42 * i} for i in range(30_000)
    ]
    Entry.single_register(
        method=Entry.POST,
        uri=test_uri,
        body=json.dumps(
            response,
        ),
        headers={"content-type": "application/json"},
    )

    with httpx.Client() as client:
        response = client.post(test_uri)

    assert len(response.json())


@pytest.mark.asyncio
@async_mocketize(strict_mode=True)
async def test_async_case_low_number():
    test_uri = "https://abc.de/testdata/"
    base_timestamp = int(datetime.datetime.now().timestamp())
    response = [
        {"timestamp": base_timestamp + i, "value": 1337 + 42 * i} for i in range(100)
    ]
    Entry.single_register(
        method=Entry.POST,
        uri=test_uri,
        body=json.dumps(
            response,
        ),
        headers={"content-type": "application/json"},
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(test_uri)

    assert len(response.json())


@pytest.mark.asyncio
@async_mocketize(strict_mode=True)
async def test_async_case_high_number():
    test_uri = "https://abc.de/testdata/"
    base_timestamp = int(datetime.datetime.now().timestamp())
    response = [
        {"timestamp": base_timestamp + i, "value": 1337 + 42 * i} for i in range(30_000)
    ]
    Entry.single_register(
        method=Entry.POST,
        uri=test_uri,
        body=json.dumps(
            response,
        ),
        headers={"content-type": "application/json"},
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(test_uri)

    assert len(response.json())


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
