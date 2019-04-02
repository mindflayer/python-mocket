===============
mocket /mɔˈkɛt/
===============

.. image:: https://api.shippable.com/projects/5af070d0a55fb8070034316f/badge?branch=master
    :target: https://app.shippable.com/github/mindflayer/python-mocket

.. image:: https://coveralls.io/repos/github/mindflayer/python-mocket/badge.svg?branch=master
    :target: https://coveralls.io/github/mindflayer/python-mocket?branch=master

.. image:: https://codeclimate.com/github/mindflayer/python-mocket/badges/gpa.svg
   :target: https://codeclimate.com/github/mindflayer/python-mocket
   :alt: Code Climate

.. image:: https://requires.io/github/mindflayer/python-mocket/requirements.svg?branch=master
     :target: https://requires.io/github/mindflayer/python-mocket/requirements/?branch=master
     :alt: Requirements Status

A socket mock framework
-------------------------
    for all kinds of socket *animals*, web-clients included - with gevent/asyncio/SSL support

Support it
==========
*Star* the project on GitHub, Buy Me a Coffee or, even better, contribute with patches or documentation.

.. image:: https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png
     :target: https://www.buymeacoffee.com/mULbInw5z
     :alt: Buy Me A Coffee

How to use it
=============
Read these three blog posts if you want to have a big picture of what *Mocket* is capable of:

- https://medium.com/p/mocket-is-alive-and-is-fighting-with-us-b2810d52597a
- https://hackernoon.com/make-development-great-again-faab769d264e
- https://hackernoon.com/httpretty-now-supports-asyncio-e310814704c6

The starting point to understand how to use *Mocket* to write a custom mock is the following example:

- https://github.com/mindflayer/mocketoy

As next step, you are invited to have a look at both the implementation of the two mocks it provides:

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

Quick example of its HTTP mock
==============================
Let's create a new virtualenv with all we need::

    $ virtualenv example
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

HTTPretty compatibility layer
=============================
Mocket HTTP mock can work as *HTTPretty* replacement for many different use cases. Two main features are missing:

- URL entries containing regular expressions;
- response body from functions.

Two features which are against the Zen of Python, at least imho (mindflayer), but of course I am open to call it into question.

Example:

.. code-block:: python

    import json

    import aiohttp
    import asyncio
    import async_timeout
    from unittest import TestCase

    from mocket.plugins.httpretty import HTTPretty, httprettified


    class AioHttpEntryTestCase(TestCase):
        @httprettified
        def test_https_session(self):
            url = 'https://httpbin.org/ip'
            HTTPretty.register_uri(
                HTTPretty.GET,
                url,
                body=json.dumps(dict(origin='127.0.0.1')),
            )

            async def main(l):
                async with aiohttp.ClientSession(loop=l) as session:
                    with async_timeout.timeout(3):
                        async with session.get(url) as get_response:
                            assert get_response.status == 200
                            assert await get_response.text() == '{"origin": "127.0.0.1"}'

            loop = asyncio.get_event_loop()
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
                async with aiohttp.ClientSession(loop=l) as session:
                    with async_timeout.timeout(3):
                        async with session.get(url) as get_response:
                            assert get_response.status == 404
                            assert await get_response.text() == body

                    with async_timeout.timeout(3):
                        async with session.post(url, data=body * 6) as post_response:
                            assert post_response.status == 201
                            assert await post_response.text() == body * 2

            loop = asyncio.get_event_loop()
            loop.run_until_complete(main(loop))

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
