# -*- coding: utf-8 -*-

# <HTTPretty - HTTP client mock for Python>
# Copyright (C) <2011-2015>  Gabriel Falcão <gabriel@nacaolivre.org>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

from __future__ import unicode_literals

import requests
from sure import expect

from mocket.plugins.httpretty import HTTPretty, httprettified, httpretty


@httprettified
def test_httpretty_should_mock_a_simple_get_with_requests_read():
    """HTTPretty should mock a simple GET with requests.get"""

    httpretty.register_uri(
        httpretty.GET, "http://yipit.com/", body="Find the best daily deals"
    )

    response = requests.get("http://yipit.com")
    expect(response.text).to.equal("Find the best daily deals")
    expect(httpretty.last_request.method).to.equal("GET")
    expect(httpretty.last_request.path).to.equal("/")


@httprettified
def test_httpretty_provides_easy_access_to_querystrings():
    """HTTPretty should provide an easy access to the querystring"""

    HTTPretty.register_uri(
        HTTPretty.GET, "http://yipit.com/", body="Find the best daily deals"
    )

    requests.get("http://yipit.com/?foo=bar&foo=baz&chuck=norris")
    expect(HTTPretty.last_request.querystring).to.equal(
        {"foo": ["bar", "baz"], "chuck": ["norris"],}
    )


@httprettified
def test_httpretty_should_mock_headers_requests():
    """HTTPretty should mock basic headers with requests"""

    HTTPretty.register_uri(
        HTTPretty.GET,
        "http://github.com/",
        body="this is supposed to be the response",
        status=201,
    )

    response = requests.get("http://github.com")
    expect(response.status_code).to.equal(201)

    expect(dict(response.headers)).to.equal(
        {
            "content-type": "text/plain; charset=utf-8",
            "connection": "close",
            "content-length": "35",
            "status": "201",
            "server": "Python/HTTPretty",
            "date": response.headers["date"],
        }
    )


@httprettified
def test_httpretty_should_allow_adding_and_overwritting_requests():
    """HTTPretty should allow adding and overwritting headers with requests"""

    HTTPretty.register_uri(
        HTTPretty.GET,
        "http://github.com/foo",
        body="this is supposed to be the response",
        adding_headers={
            "Server": "Apache",
            "Content-Length": "27",
            "Content-Type": "application/json",
        },
    )

    response = requests.get("http://github.com/foo")

    expect(dict(response.headers)).to.equal(
        {
            "content-type": "application/json",
            "connection": "close",
            "content-length": "27",
            "status": "200",
            "server": "Apache",
            "date": response.headers["date"],
        }
    )


@httprettified
def test_httpretty_should_allow_forcing_headers_requests():
    """HTTPretty should allow forcing headers with requests"""

    HTTPretty.register_uri(
        HTTPretty.GET,
        "http://github.com/foo",
        body="<root><baz /</root>",
        forcing_headers={"Content-Type": "application/xml", "Content-Length": "19",},
    )

    response = requests.get("http://github.com/foo")

    expect(dict(response.headers)).to.equal(
        {"content-type": "application/xml", "content-length": "19",}
    )


@httprettified
def test_httpretty_should_allow_adding_and_overwritting_by_kwargs_u2():
    """HTTPretty should allow adding and overwritting headers by keyword args " \
        "with requests"""

    HTTPretty.register_uri(
        HTTPretty.GET,
        "http://github.com/foo",
        body="this is supposed to be the response",
        server="Apache",
        content_length="27",
        content_type="application/json",
    )

    response = requests.get("http://github.com/foo")

    expect(dict(response.headers)).to.equal(
        {
            "content-type": "application/json",
            "connection": "close",
            "content-length": "27",
            "status": "200",
            "server": "Apache",
            "date": response.headers["date"],
        }
    )


@httprettified
def test_rotating_responses_with_requests():
    """HTTPretty should support rotating responses with requests"""

    HTTPretty.register_uri(
        HTTPretty.GET,
        "https://api.yahoo.com/test",
        responses=[
            HTTPretty.Response(body=b"first response", status=201),
            HTTPretty.Response(body=b"second and last response", status=202),
        ],
    )

    response1 = requests.get("https://api.yahoo.com/test")

    expect(response1.status_code).to.equal(201)
    expect(response1.text).to.equal("first response")

    response2 = requests.get("https://api.yahoo.com/test")

    expect(response2.status_code).to.equal(202)
    expect(response2.text).to.equal("second and last response")

    response3 = requests.get("https://api.yahoo.com/test")

    expect(response3.status_code).to.equal(202)
    expect(response3.text).to.equal("second and last response")


@httprettified
def test_can_inspect_last_request():
    """HTTPretty.last_request is a mimetools.Message request from last match"""

    HTTPretty.register_uri(
        HTTPretty.POST,
        "http://api.github.com/",
        body='{"repositories": ["HTTPretty", "lettuce"]}',
    )

    response = requests.post(
        "http://api.github.com",
        '{"username": "gabrielfalcao"}',
        headers={"content-type": "text/json",},
    )

    expect(HTTPretty.last_request.method).to.equal("POST")
    expect(HTTPretty.last_request.body).to.equal(b'{"username": "gabrielfalcao"}',)
    expect(HTTPretty.last_request.headers["content-type"]).to.equal("text/json",)
    expect(response.json()).to.equal({"repositories": ["HTTPretty", "lettuce"]})


@httprettified
def test_can_inspect_last_request_with_ssl():
    """HTTPretty.last_request is recorded even when mocking 'https' (SSL)"""

    HTTPretty.register_uri(
        HTTPretty.POST,
        "https://secure.github.com/",
        body='{"repositories": ["HTTPretty", "lettuce"]}',
    )

    response = requests.post(
        "https://secure.github.com",
        '{"username": "gabrielfalcao"}',
        headers={"content-type": "text/json",},
    )

    expect(HTTPretty.last_request.method).to.equal("POST")
    expect(HTTPretty.last_request.body).to.equal(b'{"username": "gabrielfalcao"}',)
    expect(HTTPretty.last_request.headers["content-type"]).to.equal("text/json",)
    expect(response.json()).to.equal({"repositories": ["HTTPretty", "lettuce"]})


@httprettified
def test_httpretty_ignores_querystrings_from_registered_uri():
    """HTTPretty should ignore querystrings from the registered uri (requests library)"""

    HTTPretty.register_uri(
        HTTPretty.GET, "http://yipit.com/?id=123", body=b"Find the best daily deals"
    )

    response = requests.get("http://yipit.com/", params={"id": 123})
    expect(response.text).to.equal("Find the best daily deals")
    expect(HTTPretty.last_request.method).to.equal("GET")
    expect(HTTPretty.last_request.path).to.equal("/?id=123")


@httprettified
def test_multiline():
    url = "http://httpbin.org/post"
    data = b"content=Im\r\na multiline\r\n\r\nsentence\r\n"
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
        "Accept": "text/plain",
    }
    HTTPretty.register_uri(
        HTTPretty.POST, url,
    )
    response = requests.post(url, data=data, headers=headers)

    expect(response.status_code).to.equal(200)
    expect(HTTPretty.last_request.method).to.equal("POST")
    expect(HTTPretty.last_request.path).to.equal("/post")
    expect(HTTPretty.last_request.body).to.equal(data)
    expect(HTTPretty.last_request.headers["content-length"]).to.equal("37")
    expect(HTTPretty.last_request.headers["content-type"]).to.equal(
        "application/x-www-form-urlencoded; charset=utf-8"
    )
    expect(len(HTTPretty.latest_requests)).to.equal(1)


@httprettified
def test_multipart():
    url = "http://httpbin.org/post"
    data = b'--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="content"\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 68\r\n\r\nAction: comment\nText: Comment with attach\nAttachment: x1.txt, x2.txt\r\n--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="attachment_2"; filename="x.txt"\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\nbye\n\r\n--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="attachment_1"; filename="x.txt"\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\nbye\n\r\n--xXXxXXyYYzzz--\r\n'
    headers = {
        "Content-Length": "495",
        "Content-Type": "multipart/form-data; boundary=xXXxXXyYYzzz",
        "Accept": "text/plain",
    }
    HTTPretty.register_uri(
        HTTPretty.POST, url,
    )
    response = requests.post(url, data=data, headers=headers)
    expect(response.status_code).to.equal(200)
    expect(HTTPretty.last_request.method).to.equal("POST")
    expect(HTTPretty.last_request.path).to.equal("/post")
    expect(HTTPretty.last_request.body).to.equal(data)
    expect(HTTPretty.last_request.headers["content-length"]).to.equal("495")
    expect(HTTPretty.last_request.headers["content-type"]).to.equal(
        "multipart/form-data; boundary=xXXxXXyYYzzz"
    )
    expect(len(HTTPretty.latest_requests)).to.equal(1)


@httprettified
def test_httpretty_should_allow_multiple_methods_for_the_same_uri():
    """HTTPretty should allow registering multiple methods for the same uri"""

    url = "http://test.com/test"
    methods = ["GET", "POST", "PUT", "OPTIONS"]
    for method in methods:
        HTTPretty.register_uri(getattr(HTTPretty, method), url, method)

    for method in methods:
        request_action = getattr(requests, method.lower())
        expect(request_action(url).text).to.equal(method)


@httprettified
def test_httpretty_should_allow_multiple_responses_with_multiple_methods():
    """HTTPretty should allow multiple responses when binding multiple methods to the same uri"""

    url = "http://test.com/list"

    # add get responses
    HTTPretty.register_uri(
        HTTPretty.GET,
        url,
        responses=[HTTPretty.Response(body="a"), HTTPretty.Response(body="b")],
    )

    # add post responses
    HTTPretty.register_uri(
        HTTPretty.POST,
        url,
        responses=[HTTPretty.Response(body="c"), HTTPretty.Response(body="d")],
    )

    expect(requests.get(url).text).to.equal("a")
    expect(requests.post(url).text).to.equal("c")

    expect(requests.get(url).text).to.equal("b")
    expect(requests.get(url).text).to.equal("b")
    expect(requests.get(url).text).to.equal("b")

    expect(requests.post(url).text).to.equal("d")
    expect(requests.post(url).text).to.equal("d")
    expect(requests.post(url).text).to.equal("d")


@httprettified
def test_lack_of_trailing_slash():
    """HTTPretty should automatically append a slash to given urls"""
    url = "http://www.youtube.com"
    HTTPretty.register_uri(HTTPretty.GET, url, body="")
    response = requests.get(url)
    expect(response.status_code).should.equal(200)


@httprettified
def test_unicode_querystrings():
    """Querystrings should accept unicode characters"""
    HTTPretty.register_uri(
        HTTPretty.GET, "http://yipit.com/login", body="Find the best daily deals"
    )
    requests.get("http://yipit.com/login?user=Gabriel+Falcão")
    expect(HTTPretty.last_request.querystring["user"][0]).should.be.equal(
        "Gabriel Falcão"
    )
