===============
mocket /mɔˈkɛt/
===============

.. image:: https://api.travis-ci.org/mocketize/python-mocket.png?branch=master
    :target: http://travis-ci.org/mocketize/python-mocket

.. image:: https://coveralls.io/repos/mocketize/python-mocket/badge.png?branch=master
    :target: https://coveralls.io/r/mocketize/python-mocket

A socket mock framework
-----------------------

Installation
============
Using pip::

    $ pip install mocket

Issues
============
When opening an **Issue**, please add few lines of code as failing test, or -better- open its relative **Pull request** adding this test to our test suite.

Quick example
=============
Let's create a new virtualenv with all we need::

    $ virtualenv example
    $ source example/bin/activate
    $ pip install pytest requests mocket

As second step, we create an `example.py` file as the following one:

.. code-block:: python

    import json
 
    from mocket.mocket import mocketize
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
        url_to_mock = 'http://testme.org/json'
 
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

Video presentation
==================
EuroPython 2013, Florence

https://www.youtube.com/watch?v=-LvXbl5d02U

.. image:: http://badge.kloud51.com/pypi/v/mocket.png

.. image:: http://badge.kloud51.com/pypi/d/mocket.png

.. image:: http://badge.kloud51.com/pypi/w/mocket.png

.. image:: http://badge.kloud51.com/pypi/e/mocket.png

.. image:: http://badge.kloud51.com/pypi/l/mocket.png

.. image:: http://badge.kloud51.com/pypi/f/mocket.png

.. image:: http://badge.kloud51.com/pypi/py_versions/mocket.png

.. image:: http://badge.kloud51.com/pypi/s/mocket.png
