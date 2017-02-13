===============
mocket /mɔˈkɛt/
===============

.. image:: https://api.travis-ci.org/mindflayer/python-mocket.svg?branch=master
    :target: http://travis-ci.org/mindflayer/python-mocket

.. image:: https://coveralls.io/repos/github/mindflayer/python-mocket/badge.svg?branch=master
    :target: https://coveralls.io/github/mindflayer/python-mocket?branch=master

.. image:: https://codeclimate.com/github/mindflayer/python-mocket/badges/gpa.svg
   :target: https://codeclimate.com/github/mindflayer/python-mocket
   :alt: Code Climate

A socket mock framework
-------------------------
    for all kinds of socket *animals*, web-clients included - with gevent/asyncio/SSL support

How to use it
=============
The starting point to understand how to use *Mocket* to write a custom mock is the following example:

- https://github.com/mindflayer/mocketoy

Next step, you are invited to have a look at both the implementation of the two mocks we provide:

- HTTP mock (similar to HTTPretty) - https://github.com/mindflayer/python-mocket/blob/master/mocket/mockhttp.py
- Redis mock (basic implementation) - https://github.com/mindflayer/python-mocket/blob/master/mocket/mockredis.py

Please also have a look at the huge test suite:

- Tests module at https://github.com/mindflayer/python-mocket/tree/master/tests

Installation
============
Using pip::

    $ pip install mocket

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
 
 
    @mocketize
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


Let's fire our example test::

    $ py.test example.py

Works well with others
=======================
Using *Mocket* as pook_ engine::

    $ pip install mocket[pook]

.. _pook: https://pypi.python.org/pypi/pook

Example:

.. code-block:: python

    import pook
    from mocket.plugins.pook_mock_engine import MocketEngine
    
    pook.activate()

    pook.set_mock_engine(MocketEngine)

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

    pook.disable()


First appearance
================
EuroPython 2013, Florence

- Video: https://www.youtube.com/watch?v=-LvXbl5d02U
- Slides: https://prezi.com/tmuiaugamsti/mocket/
- Slides as PDF: https://ep2013.europython.eu/media/conference/slides/mocket-a-socket-mock-framework.pdf

.. image:: http://badge.kloud51.com/pypi/v/mocket.svg

.. image:: http://badge.kloud51.com/pypi/d/mocket.svg

.. image:: http://badge.kloud51.com/pypi/w/mocket.svg

.. image:: http://badge.kloud51.com/pypi/e/mocket.svg

.. image:: http://badge.kloud51.com/pypi/l/mocket.svg

.. image:: http://badge.kloud51.com/pypi/f/mocket.svg

.. image:: http://badge.kloud51.com/pypi/py_versions/mocket.svg

.. image:: http://badge.kloud51.com/pypi/s/mocket.svg
