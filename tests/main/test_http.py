# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import io
import json
import os
import socket
import tempfile
import time
from unittest import TestCase

import mock
import pytest
import requests

from mocket import Mocket, mocketize
from mocket.mockhttp import Entry, Response
from tests import HTTPError, urlencode, urlopen

recording_directory = tempfile.mkdtemp()


class HttpTestCase(TestCase):
    def assertEqualHeaders(self, first, second, msg=None):
        first = dict((k.lower(), v) for k, v in first.items())
        second = dict((k.lower(), v) for k, v in second.items())
        self.assertEqual(first, second, msg)


@pytest.mark.skipif('os.getenv("SKIP_TRUE_HTTP", False)')
class TrueHttpEntryTestCase(HttpTestCase):
    @mocketize
    def test_truesendall(self):
        url = "http://httpbin.org/ip"
        resp = urlopen(url)
        self.assertEqual(resp.code, 200)
        resp = requests.get(url)
        self.assertEqual(resp.status_code, 200)

    @mocketize(truesocket_recording_dir=recording_directory)
    def test_truesendall_with_recording(self):
        url = "http://httpbin.org/ip"

        urlopen(url)
        requests.get(url)
        resp = urlopen(url)
        self.assertEqual(resp.code, 200)
        resp = requests.get(url)
        self.assertEqual(resp.status_code, 200)
        assert "origin" in resp.json()

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(), Mocket.get_namespace() + ".json"
        )
        with io.open(dump_filename) as f:
            responses = json.load(f)

        self.assertEqual(len(responses["httpbin.org"]["80"].keys()), 2)

    @mocketize(truesocket_recording_dir=recording_directory)
    def test_truesendall_with_gzip_recording(self):
        url = "http://httpbin.org/gzip"

        requests.get(url)
        resp = requests.get(url)
        self.assertEqual(resp.status_code, 200)

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(), Mocket.get_namespace() + ".json"
        )
        with io.open(dump_filename) as f:
            responses = json.load(f)

        assert len(responses["httpbin.org"]["80"].keys()) == 1

    @mocketize(truesocket_recording_dir=recording_directory)
    def test_truesendall_with_chunk_recording(self):
        url = "http://httpbin.org/range/70000?chunk_size=65536"

        requests.get(url)
        resp = requests.get(url)
        self.assertEqual(resp.status_code, 200)

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(), Mocket.get_namespace() + ".json"
        )
        with io.open(dump_filename) as f:
            responses = json.load(f)

        assert len(responses["httpbin.org"]["80"].keys()) == 1

    @mocketize
    def test_wrongpath_truesendall(self):
        Entry.register(Entry.GET, "http://httpbin.org/user.agent", Response(status=404))
        response = urlopen("http://httpbin.org/ip")
        self.assertEqual(response.code, 200)


class HttpEntryTestCase(HttpTestCase):
    def test_register(self):
        with mock.patch("time.gmtime") as tt:
            tt.return_value = time.struct_time((2013, 4, 30, 10, 39, 21, 1, 120, 0))
            Entry.register(
                Entry.GET,
                "http://testme.org/get?a=1&b=2#test",
                Response('{"a": "€"}', headers={"content-type": "application/json"}),
            )
        entries = Mocket._entries[("testme.org", 80)]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.method, "GET")
        self.assertEqual(entry.schema, "http")
        self.assertEqual(entry.path, "/get")
        self.assertEqual(entry.query, "a=1&b=2")
        self.assertEqual(len(entry.responses), 1)
        response = entry.responses[0]
        self.assertEqual(response.body, b'{"a": "\xe2\x82\xac"}')
        self.assertEqual(response.status, 200)
        self.assertEqual(
            response.headers,
            {
                "Status": "200",
                "Date": "Tue, 30 Apr 2013 10:39:21 GMT",
                "Connection": "close",
                "Server": "Python/Mocket",
                "Content-Length": "12",
                "Content-Type": "application/json",
            },
        )

    @mocketize
    def test_sendall(self):
        with mock.patch("time.gmtime") as tt:
            tt.return_value = time.struct_time((2013, 4, 30, 10, 39, 21, 1, 120, 0))
            Entry.single_register(
                Entry.GET, "http://testme.org/get/p/?a=1&b=2", body="test_body"
            )
        resp = urlopen("http://testme.org/get/p/?b=2&a=1", timeout=10)
        self.assertEqual(resp.code, 200)
        self.assertEqual(resp.read(), b"test_body")
        self.assertEqualHeaders(
            dict(resp.headers),
            {
                "Status": "200",
                "Content-length": "9",
                "Server": "Python/Mocket",
                "Connection": "close",
                "Date": "Tue, 30 Apr 2013 10:39:21 GMT",
                "Content-type": "text/plain; charset=utf-8",
            },
        )
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_sendall_json(self):
        with mock.patch("time.gmtime") as tt:
            tt.return_value = time.struct_time((2013, 4, 30, 10, 39, 21, 1, 120, 0))
            Entry.single_register(
                Entry.GET,
                "http://testme.org/get?a=1&b=2#test",
                body='{"a": "€"}',
                headers={"content-type": "application/json"},
            )

        response = urlopen("http://testme.org/get?b=2&a=1#test", timeout=10)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.read(), b'{"a": "\xe2\x82\xac"}')
        self.assertEqualHeaders(
            dict(response.headers),
            {
                "status": "200",
                "content-length": "12",
                "server": "Python/Mocket",
                "connection": "close",
                "date": "Tue, 30 Apr 2013 10:39:21 GMT",
                "content-type": "application/json",
            },
        )
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_sendall_double(self):
        Entry.register(
            Entry.GET, "http://testme.org/", Response(status=404), Response()
        )
        self.assertRaises(HTTPError, urlopen, "http://testme.org/")
        response = urlopen("http://testme.org/")
        self.assertEqual(response.code, 200)
        response = urlopen("http://testme.org/")
        self.assertEqual(response.code, 200)
        self.assertEqual(len(Mocket._requests), 3)

    @mocketize
    def test_mockhttp_entry_collect_duplicates(self):
        Entry.single_register(
            Entry.POST, "http://testme.org/", status=200, match_querystring=False
        )
        requests.post(
            "http://testme.org/?foo=bar",
            data="{'foo': 'bar'}",
            headers={"content-type": "application/json"},
        )
        requests.post("http://testme.org/")
        self.assertEqual(len(Mocket._requests), 2)
        self.assertEqual(Mocket.last_request().path, "/")

    @mocketize
    def test_multipart(self):
        url = "http://httpbin.org/post"
        data = '--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="content"\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 68\r\n\r\nAction: comment\nText: Comment with attach\nAttachment: x1.txt, x2.txt\r\n--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="attachment_2"; filename="x.txt"\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\nbye\n\r\n--xXXxXXyYYzzz\r\nContent-Disposition: form-data; name="attachment_1"; filename="x.txt"\r\nContent-Type: text/plain\r\nContent-Length: 4\r\n\r\nbye\n\r\n--xXXxXXyYYzzz--\r\n'
        headers = {
            "Content-Length": "495",
            "Content-Type": "multipart/form-data; boundary=xXXxXXyYYzzz",
            "Accept": "text/plain",
            "User-Agent": "Mocket",
            "Accept-encoding": "identity",
        }
        Entry.register(Entry.POST, url)
        response = requests.post(url, data=data, headers=headers)
        self.assertEqual(response.status_code, 200)
        last_request = Mocket.last_request()
        self.assertEqual(last_request.method, "POST")
        self.assertEqual(last_request.path, "/post")
        self.assertEqual(last_request.body, data)
        sent_headers = dict(last_request.headers)
        self.assertEqualHeaders(
            sent_headers,
            {
                "accept": "text/plain",
                "accept-encoding": "identity",
                "content-length": "495",
                "content-type": "multipart/form-data; boundary=xXXxXXyYYzzz",
                "host": "httpbin.org",
                "user-agent": "Mocket",
                "connection": "keep-alive",
            },
        )
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_file_object(self):
        url = "http://github.com/fluidicon.png"
        filename = "tests/fluidicon.png"
        file_obj = open(filename, "rb")
        Entry.single_register(Entry.GET, url, body=file_obj)
        r = requests.get(url)
        remote_content = r.content
        local_file_obj = open(filename, "rb")
        local_content = local_file_obj.read()
        self.assertEqual(remote_content, local_content)
        self.assertEqual(len(remote_content), len(local_content))
        self.assertEqual(int(r.headers["Content-Length"]), len(local_content))
        self.assertEqual(r.headers["Content-Type"], "image/png")

    @mocketize
    def test_file_object_with_no_lib_magic(self):
        url = "http://github.com/fluidicon.png"
        filename = "tests/fluidicon.png"
        file_obj = open(filename, "rb")
        Entry.register(Entry.GET, url, Response(body=file_obj, lib_magic=None))
        r = requests.get(url)
        remote_content = r.content
        local_file_obj = open(filename, "rb")
        local_content = local_file_obj.read()
        self.assertEqual(remote_content, local_content)
        self.assertEqual(len(remote_content), len(local_content))
        self.assertEqual(int(r.headers["Content-Length"]), len(local_content))
        with self.assertRaises(KeyError):
            self.assertEqual(r.headers["Content-Type"], "image/png")

    @mocketize
    def test_same_url_different_methods(self):
        url = "http://bit.ly/fakeurl"
        response_to_mock = {"content": 0, "method": None}
        responses = []
        methods = [Entry.PUT, Entry.GET, Entry.POST]

        for m in methods:
            response_to_mock["method"] = m
            Entry.single_register(m, url, body=json.dumps(response_to_mock))
            response_to_mock["content"] += 1
        for m in methods:
            responses.append(requests.request(m, url).json())

        methods_from_responses = [r["method"] for r in responses]
        contents_from_responses = [r["content"] for r in responses]
        self.assertEqual(methods, methods_from_responses)
        self.assertEqual(list(range(len(methods))), contents_from_responses)

    @mocketize
    def test_request_bodies(self):
        url = "http://bit.ly/fakeurl/{0}"

        for e in range(5):
            u = url.format(e)
            Entry.single_register(Entry.POST, u, body=str(e))
            request_body = urlencode({"key-{0}".format(e): "value={0}".format(e)})
            urlopen(u, request_body.encode("utf-8"))
            last_request = Mocket.last_request()
            assert last_request.body == request_body

    @mocketize(truesocket_recording_dir=os.path.dirname(__file__))
    def test_truesendall_with_dump_from_recording(self):
        requests.get("http://httpbin.org/ip", headers={"user-agent": "Fake-User-Agent"})
        requests.get(
            "http://httpbin.org/gzip", headers={"user-agent": "Fake-User-Agent"}
        )

        dump_filename = os.path.join(
            Mocket.get_truesocket_recording_dir(), Mocket.get_namespace() + ".json"
        )
        with io.open(dump_filename) as f:
            responses = json.load(f)

        self.assertEqual(len(responses["httpbin.org"]["80"].keys()), 2)

    @mocketize
    def test_post_file_object(self):
        url = "http://github.com/fluidicon.png"
        Entry.single_register(Entry.POST, url, status=201)
        file_obj = open("tests/fluidicon.png", "rb")
        files = {"content": file_obj}
        r = requests.post(url, files=files, data={}, verify=False)
        self.assertEqual(r.status_code, 201)

    @mocketize
    def test_raise_exception(self):
        url = "http://github.com/fluidicon.png"
        Entry.single_register(Entry.GET, url, exception=socket.error())
        with self.assertRaises(requests.exceptions.ConnectionError):
            requests.get(url)

    @mocketize
    def test_sockets(self):
        """
        https://github.com/mindflayer/python-mocket/issues/111
        https://gist.github.com/amotl/015ef6b336db55128798d7f1a9a67dea
        """

        # Define HTTP conversation.
        url = "http://127.0.0.1:8080/api/data"
        Entry.single_register(Entry.POST, url)

        # Define HTTP url segments and data.
        host = "127.0.0.1"
        port = 8080
        method = "POST"
        path = "/api/data"
        data = json.dumps({"hello": "world"})

        # Invoke HTTP request.
        address = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)[0]
        sock = socket.socket(address[0], address[1], address[2])

        sock.connect(address[-1])
        sock.write("%s %s HTTP/1.0\r\n" % (method, path))
        sock.write("Host: %s\r\n" % host)
        sock.write("Content-Type: application/json\r\n")
        sock.write("Content-Length: %d\r\n" % len(data))
        sock.write("Connection: close\r\n\r\n")
        sock.write(data)
        sock.close()

        # Proof that worked.
        self.assertEqual(Mocket.last_request().body, '{"hello": "world"}')

    @mocketize
    def test_fail_because_entry_not_served(self):
        url = "http://github.com/fluidicon.png"
        Entry.single_register(Entry.GET, url)
        Entry.single_register(Entry.GET, "http://github.com/fluidicon.jpg")
        requests.get(url)
        with self.assertRaises(AssertionError):
            Mocket.assert_fail_if_entries_not_served()

    @mocketize
    def test_does_not_fail_because_all_entries_are_served(self):
        url = "http://github.com/fluidicon.png"
        second_url = "http://github.com/fluidicon.jpg"
        Entry.single_register(Entry.GET, url)
        Entry.single_register(Entry.GET, second_url)
        requests.get(url)
        requests.get(second_url)
        Mocket.assert_fail_if_entries_not_served()
