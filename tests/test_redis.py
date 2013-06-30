# coding=utf-8
import redis
from unittest import TestCase
from mocket.mockredis import Entry
from mocket.registry import mocketize, Mocket


class RedisEntryTestCase(TestCase):
    def mocketize_setup(self):
        self.rclient = redis.StrictRedis()

    @mocketize
    def test_truesendall_set(self):
        try:
            self.rclient.flushall()
        except redis.ConnectionError:
            return
        self.assertTrue(self.rclient.set('mocket', 'is awesome!'))
        self.assertEqual(len(Mocket._requests), 0)

    @mocketize
    def test_truesendall_incr(self):
        try:
            self.rclient.flushall()
        except redis.ConnectionError:
            return
        self.assertEqual(self.rclient.incr('counter'), 1)
        self.assertEqual(self.rclient.incr('counter'), 2)
        self.assertEqual(self.rclient.incr('counter'), 3)
        self.assertEqual(len(Mocket._requests), 0)

    @mocketize
    def test_truesendall_hm(self):
        try:
            self.rclient.flushall()
        except redis.ConnectionError:
            return
        h = {'f1': 'one', 'f2': 'two'}
        self.assertTrue(self.rclient.hmset('hash', h))
        self.assertEqual(self.rclient.hgetall('hash'), h)
        self.assertEqual(len(Mocket._requests), 0)

    @mocketize
    def test_sendall_set(self):
        Entry.single_register('SET mocket "is awesome!"', '+OK')
        self.assertTrue(self.rclient.set('mocket', 'is awesome!'))
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket.last_request().data, '*3\r\n$3\r\nSET\r\n$6\r\nmocket\r\n$11\r\nis awesome!\r\n')

    @mocketize
    def test_sendall_incr(self):
        Entry.multi_register('INCRBY counter 1', (Entry.redis_int(1), Entry.redis_int(2), Entry.redis_int(3)))
        self.assertEqual(self.rclient.incr('counter'), 1)
        self.assertEqual(self.rclient.incr('counter'), 2)
        self.assertEqual(self.rclient.incr('counter'), 3)
        self.assertEqual(len(Mocket._requests), 3)
        self.assertEqual(Mocket._requests[0].data, '*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n')
        self.assertEqual(Mocket._requests[1].data, '*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n')
        self.assertEqual(Mocket._requests[2].data, '*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n')

    @mocketize
    def test_sendall_hgetall(self):
        h = {'f1': 'one', 'f2': 'two'}
        Entry.single_register('HGETALL hash', Entry.redis_map({'f1': 'one', 'f2': 'two'}))
        self.assertEqual(self.rclient.hgetall('hash'), h)
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket._requests[0].data, '*2\r\n$7\r\nHGETALL\r\n$4\r\nhash\r\n')
