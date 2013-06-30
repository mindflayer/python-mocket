# coding=utf-8
import redis
from unittest import TestCase
from mocket.mockredis import Entry
from mocket.registry import Mocket, mocketize


class RedisEntryTestCase(TestCase):
    def mocketize_setup(self):
        self.rclient = redis.StrictRedis()
        self.rclient.flushall()

    @mocketize
    def test_truesendall_set(self):
        self.assertTrue(self.rclient.set('mocket', 'is awesome!'))

    @mocketize
    def test_sendall_set(self):
        Entry.single_register('SET mocket "is awesome!"', '+OK')
        self.assertTrue(self.rclient.set('mocket', 'is awesome!'))

    @mocketize
    def test_truesendall_incr(self):
        self.assertEqual(self.rclient.incr('counter'), 1)
        self.assertEqual(self.rclient.incr('counter'), 2)
        self.assertEqual(self.rclient.incr('counter'), 3)

    @mocketize
    def test_truesendall_incr(self):
        Entry.multi_register('INCR counter 1', (1, 2, 3))

        self.assertEqual(self.rclient.incr('counter'), 1)
        self.assertEqual(self.rclient.incr('counter'), 2)
        self.assertEqual(self.rclient.incr('counter'), 3)
