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

As second step, we create an `example.py` file as the following one::

    from unittest import TestCase
    import json
    
    from mocket.mocket import mocketize
    from mocket.mockhttp import Entry
    import requests
    
    class Example(TestCase):
    
        @mocketize
        def test_json(self):
            url_to_mock = 'http://testme.org/intro'
    
            response_to_mock = {
                "integer": 1,
                "string": "asd",
                "boolean": False,
            }
    
            Entry.single_register(
                Entry.GET,
                url_to_mock,
                body=json.dumps(response_to_mock),
                headers={'content-type': 'application/json'}
            )
    
            response = requests.get(url_to_mock).json()
    
            self.assertEqual(response, response_to_mock)

Let's fire our example test::

    $ py.test example.py::Example::test_json

Video presentation
==================
EuroPython 2013, Florence

https://www.youtube.com/watch?v=-LvXbl5d02U
