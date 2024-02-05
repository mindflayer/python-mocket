===============
mocket /mɔˈkɛt/
===============

.. image:: https://github.com/mindflayer/python-mocket/workflows/Mocket's%20CI/badge.svg
    :target: https://github.com/mindflayer/python-mocket/actions?query=workflow%3A%22Mocket%27s+CI%22

.. image:: https://coveralls.io/repos/github/mindflayer/python-mocket/badge.svg?branch=master
    :target: https://coveralls.io/github/mindflayer/python-mocket?branch=master

.. image:: https://app.codacy.com/project/badge/Grade/6327640518ce42adaf59368217028f14
    :target: https://www.codacy.com/gh/mindflayer/python-mocket/dashboard

.. image:: https://img.shields.io/pypi/dm/mocket
    :target: https://pypistats.org/packages/mocket


A socket mock framework
-------------------------
    for all kinds of socket *animals*, web-clients included - with gevent/asyncio/SSL support

...and then MicroPython's *urequests* (*mocket >= 3.9.1*)

Outside GitHub
==============

Mocket packages are available for `Arch Linux`_, `openSUSE`_, `NixOS`_, `ALT Linux`_ and `NetBSD`_.

.. _`Arch Linux`: https://archlinux.org/packages/extra/any/python-mocket/
.. _`openSUSE`: https://software.opensuse.org/search?baseproject=ALL&q=mocket
.. _`NixOS`: https://search.nixos.org/packages?query=mocket
.. _`ALT Linux`: https://packages.altlinux.org/en/sisyphus/srpms/python3-module-mocket/
.. _`NetBSD`: https://cdn.netbsd.org/pub/pkgsrc/current/pkgsrc/devel/py-mocket/index.html


Versioning
==========
Starting from *3.7.0*, Mocket major version will follow the same numbering pattern as Python's and therefore indicate the most recent Python version that is supported.

FYI: the last version compatible with Python 2.7 is *3.9.4*, bugfixing or backporting of features introduced after that release will only be available as commercial support.

Support it
==========
*Star* the project on GitHub, *Buy Me a Coffee* clicking the button below or, even better, contribute with patches or documentation.

.. image:: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
     :target: https://www.buymeacoffee.com/mocket
     :alt: Buy Me A Coffee

How to use it
=============
Read the following blog posts if you want to have a big picture of what *Mocket* is capable of:

- https://medium.com/p/mocket-is-alive-and-is-fighting-with-us-b2810d52597a
- https://hackernoon.com/make-development-great-again-faab769d264e
- https://hackernoon.com/httpretty-now-supports-asyncio-e310814704c6
- https://medium.com/@mindflayer/how-to-make-your-tests-fail-when-they-try-to-access-the-network-python-eb80090a6d24
- https://medium.com/@mindflayer/testing-in-an-asyncio-world-a9a0ad41b0c5

The starting point to understand how to use *Mocket* to write a custom mock is the following example:

- https://github.com/mindflayer/mocketoy

As next step, you are invited to have a look at the implementation of both the mocks it provides:

- HTTP mock (similar to HTTPretty) - https://github.com/mindflayer/python-mocket/blob/master/mocket/mockhttp.py
- Redis mock (basic implementation) - https://github.com/mindflayer/python-mocket/blob/master/mocket/mockredis.py

Please also have a look at the huge test suite:

- Tests module at https://github.com/mindflayer/python-mocket/tree/master/tests

Installation
============
Using pip::

    $ pip install mocket

Speedups
========
Mocket uses **xxhash** when available instead of *hashlib.md5* for creating hashes, you can install it as follows::

    $ pip install mocket[speedups]

Issues
============
When opening an **Issue**, please add few lines of code as failing test, or -better- open its relative **Pull request** adding this test to our test suite.

Example of how to mock an HTTP[S] call
======================================
Let's create a new virtualenv with all we need::

    $ python3 -m venv example
    $ source example/bin/activate
    $ pip install pytest requests mocket

As second step, we create an `example.py` file as the following one:

.. code-block:: python

    import json

    from mocket import mocketize
    from mocket.mockhttp import Entry
    import requests
    import pytest


    @pytest.fixture
    def response():
        return {
            "integer": 1,
            "string": "asd",
            "boolean": False,
        }


    @mocketize  # use its decorator
    def test_json(response):
        url_to_mock = 'https://testme.org/json'

        Entry.single_register(
            Entry.GET,
            url_to_mock,
            body=json.dumps(response),
            headers={'content-type': 'application/json'}
        )

        mocked_response = requests.get(url_to_mock).json()

        assert response == mocked_response

    # OR use its context manager
    from mocket import Mocketizer

    def test_json_with_context_manager(response):
        url_to_mock = 'https://testme.org/json'

        Entry.single_register(
            Entry.GET,
            url_to_mock,
            body=json.dumps(response),
            headers={'content-type': 'application/json'}
        )

        with Mocketizer():
            mocked_response = requests.get(url_to_mock).json()

        assert response == mocked_response

Let's fire our example test::

    $ py.test example.py

How to make Mocket fail when it tries to write to a real `socket`?
==================================================================
NEW!!! Sometimes you just want your tests to fail when they attempt to use the network.

.. code-block:: python

    with Mocketizer(strict_mode=True):
        with pytest.raises(StrictMocketException):
            requests.get("https://duckduckgo.com/")

    # OR

    @mocketize(strict_mode=True)
    def test_get():
        with pytest.raises(StrictMocketException):
            requests.get("https://duckduckgo.com/")

You can specify exceptions as a list of hosts or host-port pairs.

.. code-block:: python

    with Mocketizer(strict_mode=True, strict_mode_allowed=["localhost", ("intake.ourmetrics.net", 443)]):
        ...

    # OR

    @mocketize(strict_mode=True, strict_mode_allowed=["localhost", ("intake.ourmetrics.net", 443)])
    def test_get():
        ...


How to be sure that all the Entry instances have been served?
=============================================================
Add this instruction at the end of the test execution:

.. code-block:: python

    Mocket.assert_fail_if_entries_not_served()

Example of how to fake socket errors
====================================

It's very important that we test non-happy paths.

.. code-block:: python

    @mocketize
    def test_raise_exception(self):
        url = "http://github.com/fluidicon.png"
        Entry.single_register(Entry.GET, url, exception=socket.error())
        with self.assertRaises(requests.exceptions.ConnectionError):
            requests.get(url)

Example of how to record real socket traffic
============================================

You probably know what *VCRpy* is capable of, that's the *mocket*'s way of achieving it:

.. code-block:: python

    @mocketize(truesocket_recording_dir=tempfile.mkdtemp())
    def test_truesendall_with_recording_https():
        url = 'https://httpbin.org/ip'

        requests.get(url, headers={"Accept": "application/json"})
        resp = requests.get(url, headers={"Accept": "application/json"})
        assert resp.status_code == 200

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(),
            Mocket.get_namespace() + '.json',
        )
        with io.open(dump_filename) as f:
            response = json.load(f)

        assert len(response['httpbin.org']['443'].keys()) == 1

HTTPretty compatibility layer
=============================
Mocket HTTP mock can work as *HTTPretty* replacement for many different use cases. Two main features are missing:

- URL entries containing regular expressions;
- response body from functions (used mostly to fake errors, *mocket* doesn't need to do it this way).

Two features which are against the Zen of Python, at least imho (*mindflayer*), but of course I am open to call it into question.

Example:

.. code-block:: python

    import json

    import aiohttp
    import asyncio
    from unittest import TestCase

    from mocket.plugins.httpretty import httpretty, httprettified


    class AioHttpEntryTestCase(TestCase):
        @httprettified
        def test_https_session(self):
            url = 'https://httpbin.org/ip'
            httpretty.register_uri(
                httpretty.GET,
                url,
                body=json.dumps(dict(origin='127.0.0.1')),
            )

            async def main(l):
                async with aiohttp.ClientSession(
                    loop=l, timeout=aiohttp.ClientTimeout(total=3)
                ) as session:
                    async with session.get(url) as get_response:
                        assert get_response.status == 200
                        assert await get_response.text() == '{"origin": "127.0.0.1"}'

            loop = asyncio.new_event_loop()
            loop.set_debug(True)
            loop.run_until_complete(main(loop))

What about the other socket animals?
====================================
Using *Mocket* with asyncio based clients::

    $ pip install aiohttp

Example:

.. code-block:: python

    class AioHttpEntryTestCase(TestCase):
        @mocketize
        def test_http_session(self):
            url = 'http://httpbin.org/ip'
            body = "asd" * 100
            Entry.single_register(Entry.GET, url, body=body, status=404)
            Entry.single_register(Entry.POST, url, body=body*2, status=201)

            async def main(l):
                async with aiohttp.ClientSession(
                    loop=l, timeout=aiohttp.ClientTimeout(total=3)
                ) as session:
                    async with session.get(url) as get_response:
                        assert get_response.status == 404
                        assert await get_response.text() == body

                    async with session.post(url, data=body * 6) as post_response:
                        assert post_response.status == 201
                        assert await post_response.text() == body * 2

            loop = asyncio.new_event_loop()
            loop.run_until_complete(main(loop))

    # or again with a unittest.IsolatedAsyncioTestCase
    from mocket.async_mocket import async_mocketize

    class AioHttpEntryTestCase(IsolatedAsyncioTestCase):
        @async_mocketize
        async def test_http_session(self):
            url = 'http://httpbin.org/ip'
            body = "asd" * 100
            Entry.single_register(Entry.GET, url, body=body, status=404)
            Entry.single_register(Entry.POST, url, body=body * 2, status=201)

            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=3)
            ) as session:
                async with session.get(url) as get_response:
                    assert get_response.status == 404
                    assert await get_response.text() == body

                async with session.post(url, data=body * 6) as post_response:
                    assert post_response.status == 201
                    assert await post_response.text() == body * 2
                    assert Mocket.last_request().method == 'POST'
                    assert Mocket.last_request().body == body * 6


Works well with others
=======================
Using *Mocket* as pook_ engine::

    $ pip install mocket[pook]

.. _pook: https://pypi.python.org/pypi/pook

Example:

.. code-block:: python

    import pook
    from mocket.plugins.pook_mock_engine import MocketEngine

    pook.set_mock_engine(MocketEngine)

    pook.on()

    url = 'http://twitter.com/api/1/foobar'
    status = 404
    response_json = {'error': 'foo'}

    mock = pook.get(
        url,
        headers={'content-type': 'application/json'},
        reply=status,
        response_json=response_json,
    )
    mock.persist()

    requests.get(url)
    assert mock.calls == 1

    resp = requests.get(url)
    assert resp.status_code == status
    assert resp.json() == response_json
    assert mock.calls == 2

First appearance
================
EuroPython 2013, Florence

- Video: https://www.youtube.com/watch?v=-LvXbl5d02U
- Slides: https://prezi.com/tmuiaugamsti/mocket/
- Slides as PDF: https://ep2013.europython.eu/media/conference/slides/mocket-a-socket-mock-framework.pdf
