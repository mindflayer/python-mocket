# coding=utf-8
import redis
from unittest import TestCase
from mocket.mockredis import Entry, OK, ERROR
from mocket.mocket import mocketize, Mocket


class TrueRedisEntryTestCase(TestCase):
    def setUp(self):
        self.rclient = redis.StrictRedis()

    def mocketize_setup(self):
        try:
            self.rclient.flushdb()
        except redis.ConnectionError:
            return

    def mocketize_teardown(self):
        self.assertEqual(len(Mocket._requests), 0)

    @mocketize
    def test_set(self):
        self.assertTrue(self.rclient.set('mocket', 'is awesome!'))

    @mocketize
    def test_incr(self):
        self.assertEqual(self.rclient.incr('counter'), 1)
        self.assertEqual(self.rclient.incr('counter'), 2)
        self.assertEqual(self.rclient.incr('counter'), 3)

    @mocketize
    def test_get(self):
        self.rclient.set('mocket', 'is awesome!')
        self.assertEqual(self.rclient.get('mocket'), 'is awesome!')

    @mocketize
    def test_get_utf8(self):
        self.rclient.set('snowman', '☃')
        self.assertEqual(self.rclient.get('snowman'), '☃')

    @mocketize
    def test_get_unicode(self):
        self.rclient.set('snowman', u'\u2603')
        self.assertEqual(self.rclient.get('snowman'), '☃')

    @mocketize
    def test_hm(self):
        h = {'f1': 'one', 'f2': 'two'}
        self.assertTrue(self.rclient.hmset('hash', h))
        self.assertEqual(self.rclient.hgetall('hash'), h)

    @mocketize
    def test_lrange(self):
        l = ['one', 'two', 'three']
        self.rclient.rpush('list', *l)
        self.assertEqual(self.rclient.lrange('list', 0, -1), l)

    @mocketize
    def test_err(self):
        self.assertRaises(redis.ResponseError, self.rclient.incr, 'counter', 'one')

class MocketRedisEntryTestCase(TestCase):
    def setUp(self):
        self.rclient = redis.StrictRedis()

    def mocketize_setup(self):
        self.rclient = redis.StrictRedis()

    @mocketize
    def test_set(self):
        Entry.single_register('SET mocket "is awesome!"', OK)
        self.assertTrue(self.rclient.set('mocket', 'is awesome!'))
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket.last_request().data, '*3\r\n$3\r\nSET\r\n$6\r\nmocket\r\n$11\r\nis awesome!\r\n')

    @mocketize
    def test_incr(self):
        Entry.multi_register('INCRBY counter 1', (1, 2, 3))
        self.assertEqual(self.rclient.incr('counter'), 1)
        self.assertEqual(self.rclient.incr('counter'), 2)
        self.assertEqual(self.rclient.incr('counter'), 3)
        self.assertEqual(len(Mocket._requests), 3)
        self.assertEqual(Mocket._requests[0].data, '*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n')
        self.assertEqual(Mocket._requests[1].data, '*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n')
        self.assertEqual(Mocket._requests[2].data, '*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$1\r\n1\r\n')

    @mocketize
    def test_hgetall(self):
        h = {'f1': 'one', 'f2': 'two'}
        Entry.single_register('HGETALL hash', {'f1': 'one', 'f2': 'two'})
        self.assertEqual(self.rclient.hgetall('hash'), h)
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket._requests[0].data, '*2\r\n$7\r\nHGETALL\r\n$4\r\nhash\r\n')

    @mocketize
    def test_get(self):
        Entry.single_register('GET mocket', 'is awesome!')
        self.assertEqual(self.rclient.get('mocket'), 'is awesome!')
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_get_utf8(self):
        Entry.single_register('GET snowman', '☃')
        self.assertEqual(self.rclient.get('snowman'), '☃')
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_get_unicode(self):
        Entry.single_register('GET snowman', u'\u2603')
        self.assertEqual(self.rclient.get('snowman'), '☃')
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_lrange(self):
        l = ['one', 'two', 'three']
        Entry.single_register('LRANGE list 0 -1', l)
        self.assertEqual(self.rclient.lrange('list', 0, -1), l)
        self.assertEqual(len(Mocket._requests), 1)

    @mocketize
    def test_err(self):
        Entry.single_register('INCRBY counter one', ERROR('ERR value is not an integer or out of range'))
        self.assertRaises(redis.ResponseError, self.rclient.incr, 'counter', 'one')
        self.assertEqual(len(Mocket._requests), 1)
