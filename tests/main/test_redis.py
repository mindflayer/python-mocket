# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import socket
from unittest import TestCase

import pytest
import redis

from mocket import Mocket, mocketize
from mocket.mockredis import ERROR, OK, Entry, Redisizer


class RedisizerTestCase(TestCase):
    def test_token(self):
        self.assertEqual(
            Redisizer.tokens(["SET", "snowman", "is ☃!"]),
            [b"*3", b"$3", b"SET", b"$7", b"snowman", b"$7", b"is \xe2\x98\x83!"],
        )

    def test_command(self):
        self.assertEqual(Redisizer.command("OK"), b"+OK\r\n")

    def test_error(self):
        self.assertEqual(
            Redisizer.error("ERR: ☃ summer"), b"-ERR: \xe2\x98\x83 summer\r\n"
        )

    def test_redisize_int(self):
        self.assertEqual(Redisizer.redisize(10), b":10\r\n")

    def test_redisize_list(self):
        self.assertEqual(
            Redisizer.redisize(["snowman", "☃"]),
            b"*2\r\n$7\r\nsnowman\r\n$3\r\n\xe2\x98\x83\r\n",
        )

    def test_redisize_dict(self):
        self.assertEqual(
            Redisizer.redisize({"snowman": "☃"}),
            b"*2\r\n$7\r\nsnowman\r\n$3\r\n\xe2\x98\x83\r\n",
        )

    def test_redisize_text(self):
        self.assertEqual(Redisizer.redisize("☃"), b"$3\r\n\xe2\x98\x83\r\n")

    def test_redisize_byte(self):
        self.assertEqual(Redisizer.redisize(b"\xe2\x98\x83"), b"$3\r\n\xe2\x98\x83\r\n")

    def test_redisize_command(self):
        self.assertEqual(Redisizer.redisize(Redisizer.command("OK")), b"+OK\r\n")


class RedisEntryTestCase(TestCase):
    def test_init_text(self):
        entry = Entry(addr=None, command='SET snowman "is ☃!"', responses=[])
        self.assertEqual(
            entry.command,
            [b"*3", b"$3", b"SET", b"$7", b"snowman", b"$7", b"is \xe2\x98\x83!"],
        )

    def test_init_byte(self):
        entry = Entry(
            addr=None, command=b'SET snowman "is \xe2\x98\x83!"', responses=[]
        )
        self.assertEqual(
            entry.command,
            [b"*3", b"$3", b"SET", b"$7", b"snowman", b"$7", b"is \xe2\x98\x83!"],
        )

    def test_can_handle(self):
        entry = Entry(addr=None, command='SET snowman "is ☃!"', responses=[])
        self.assertTrue(
            entry.can_handle(
                b"*3\r\n$3\r\nSET\r\n$7\r\nsnowman\r\n$7\r\nis \xe2\x98\x83!"
            )
        )

    def test_register(self):
        Entry.register(("localhost", 6379), 'SET snowman "is ☃!"', OK)
        self.assertEqual(
            Mocket._entries[("localhost", 6379)][0].command,
            [b"*3", b"$3", b"SET", b"$7", b"snowman", b"$7", b"is \xe2\x98\x83!"],
        )
        self.assertEqual(
            Mocket._entries[("localhost", 6379)][0].responses[0].data, b"+OK\r\n"
        )

    def test_register_response(self):
        Entry.register_response(command='SET snowman "is ☃!"', response="")


@pytest.mark.skipif('os.getenv("SKIP_TRUE_REDIS", False)')
class TrueRedisTestCase(TestCase):
    @mocketize
    def setUp(self):
        self.rclient = redis.StrictRedis()
        self.rclient.flushdb()

    def mocketize_teardown(self):
        self.assertEqual(len(Mocket._requests), 0)

    @mocketize
    def test_set(self):
        self.assertTrue(self.rclient.set("mocket", "is awesome!"))

    @mocketize
    def test_incr(self):
        self.assertEqual(self.rclient.incr("counter"), 1)
        self.assertEqual(self.rclient.incr("counter"), 2)
        self.assertEqual(self.rclient.incr("counter"), 3)

    @mocketize
    def test_get(self):
        self.rclient.set("mocket", "is awesome!")
        self.assertEqual(self.rclient.get("mocket"), b"is awesome!")

    @mocketize
    def test_get_utf8(self):
        self.rclient.set("snowman", "☃")
        self.assertEqual(self.rclient.get("snowman"), b"\xe2\x98\x83")

    @mocketize
    def test_get_unicode(self):
        self.rclient.set("snowman", "\u2603")
        self.assertEqual(self.rclient.get("snowman"), b"\xe2\x98\x83")

    @mocketize
    def test_hm(self):
        h = {b"f1": b"one", b"f2": b"two"}
        self.assertTrue(self.rclient.hmset("hash", h))
        self.assertEqual(self.rclient.hgetall("hash"), h)

    @mocketize
    def test_lrange(self):
        l = [b"one", b"two", b"three"]
        self.rclient.rpush("list", *l)
        self.assertEqual(self.rclient.lrange("list", 0, -1), l)

    @mocketize
    def test_err(self):
        self.assertRaises(redis.ResponseError, self.rclient.incr, "counter", "one")

    @mocketize
    def test_shutdown(self):
        rc = redis.StrictRedis(host="127.1.1.1")
        try:
            rc.get("foo")
        except redis.ConnectionError:
            pass

    @mocketize
    def test_select_db(self):
        r = redis.StrictRedis(db=1)
        r.set("foo", 10)
        foo = r.get("foo")
        self.assertEqual(foo, b"10")


class RedisTestCase(TestCase):
    def setUp(self):
        self.rclient = redis.StrictRedis()

    def mocketize_setup(self):
        Entry.register_response("FLUSHDB", OK)
        self.rclient.flushdb()
        self.assertEqual(len(Mocket._requests), 1)
        Mocket.reset()

    @mocketize
    def test_set(self):
        Entry.register_response('SET mocket "is awesome!"', OK)
        self.assertTrue(self.rclient.set("mocket", "is awesome!"))
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(
            Mocket.last_request().data,
            b"*3\r\n$3\r\nSET\r\n$6\r\nmocket\r\n$11\r\nis awesome!\r\n",
        )

    @mocketize
    def test_incr(self):
        Entry.register_responses("INCRBY counter 1", (1, 2, 3))
        self.assertEqual(self.rclient.incr("counter"), 1)
        self.assertEqual(self.rclient.incr("counter"), 2)
        self.assertEqual(self.rclient.incr("counter"), 3)
        self.assertEqual(len(Mocket._requests), 3)
        self.assertEqual(
            Mocket._requests[0].data,
            b"*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n",
        )
        self.assertEqual(
            Mocket._requests[1].data,
            b"*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n",
        )
        self.assertEqual(
            Mocket._requests[2].data,
            b"*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n",
        )

    @mocketize
    def test_hgetall(self):
        h = {b"f1": b"one", b"f2": b"two"}
        Entry.register_response("HGETALL hash", h)
        self.assertEqual(self.rclient.hgetall("hash"), h)
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(
            Mocket._requests[0].data, b"*2\r\n$7\r\nHGETALL\r\n$4\r\nhash\r\n"
        )

    @mocketize
    def test_get(self):
        Entry.register_response("GET mocket", "is awesome!")
        self.assertEqual(self.rclient.get("mocket"), b"is awesome!")
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(
            Mocket._requests[0].data, b"*2\r\n$3\r\nGET\r\n$6\r\nmocket\r\n"
        )

    @mocketize
    def test_get_utf8(self):
        Entry.register_response("GET snowman", "☃")
        self.assertEqual(self.rclient.get("snowman"), b"\xe2\x98\x83")
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(
            Mocket._requests[0].data, b"*2\r\n$3\r\nGET\r\n$7\r\nsnowman\r\n"
        )

    @mocketize
    def test_get_unicode(self):
        Entry.register_response("GET snowman", "\u2603")
        self.assertEqual(self.rclient.get("snowman"), b"\xe2\x98\x83")
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(
            Mocket.last_request().data, b"*2\r\n$3\r\nGET\r\n$7\r\nsnowman\r\n"
        )

    @mocketize
    def test_lrange(self):
        l = [b"one", b"two", b"three"]
        Entry.register_response("LRANGE list 0 -1", l)
        self.assertEqual(self.rclient.lrange("list", 0, -1), l)
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(
            Mocket.last_request().data,
            b"*4\r\n$6\r\nLRANGE\r\n$4\r\nlist\r\n$1\r\n0\r\n$2\r\n-1\r\n",
        )

    @mocketize
    def test_err(self):
        Entry.register_response(
            "INCRBY counter one", ERROR("ERR value is not an integer or out of range")
        )
        self.assertRaises(redis.ResponseError, self.rclient.incr, "counter", "one")
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(
            Mocket.last_request().data,
            b"*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$3\r\none\r\n",
        )

    @mocketize
    def test_raise_exception(self):
        Entry.register_response("INCRBY counter one", socket.error("Mocket rulez!"))
        self.assertRaises(
            redis.exceptions.ConnectionError, self.rclient.incr, "counter", "one"
        )
