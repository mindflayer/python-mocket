# coding=utf-8
import redis
from unittest import TestCase
from mocket.mockredis import Entry
from mocket.registry import Mocket, mocketize


class RedisEntryTestCase(TestCase):

    @mocketize
    def test_truesendall_set(self):
        rclient = redis.StrictRedis()
        response = rclient.set('mocket', 'is awesome!')
        self.assertTrue(response)

    @mocketize
    def test_sendall_set(self):
        Entry.single_register('SET "mocket" "is awesome!"', '+OK', ('localhost', 6379))
        rclient = redis.StrictRedis()
        response = rclient.set('mocket', 'is awesome!')
        self.assertTrue(response)
