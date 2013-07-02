# coding=utf-8
import pytest
import redis
from unittest import TestCase
from mocket.mockredis import Entry, OK, ERROR
from mocket.mocket import mocketize, Mocket


@pytest.mark.skipif('os.getenv("SKIP_TRUE_REDIS", False)')
class TrueRedisEntryTestCase(TestCase):
    def setUp(self):
        self.rclient = redis.StrictRedis()
        self.rclient.flushdb()

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
        Entry.register_response('FLUSHDB', OK)
        self.rclient.flushdb()
        self.assertEqual(len(Mocket._requests), 1)
        Mocket.reset()

    @mocketize
    def test_set(self):
        Entry.register_response('SET mocket "is awesome!"', OK)
        self.assertTrue(self.rclient.set('mocket', 'is awesome!'))
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket.last_request().data, '*3\r\n$3\r\nSET\r\n$6\r\nmocket\r\n$11\r\nis awesome!\r\n')

    @mocketize
    def test_incr(self):
        Entry.register_responses('INCRBY counter 1', (1, 2, 3))
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
        Entry.register_response('HGETALL hash', {'f1': 'one', 'f2': 'two'})
        self.assertEqual(self.rclient.hgetall('hash'), h)
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket._requests[0].data, '*2\r\n$7\r\nHGETALL\r\n$4\r\nhash\r\n')

    @mocketize
    def test_get(self):
        Entry.register_response('GET mocket', 'is awesome!')
        self.assertEqual(self.rclient.get('mocket'), 'is awesome!')
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket._requests[0].data, '*2\r\n$3\r\nGET\r\n$6\r\nmocket\r\n')

    @mocketize
    def test_get_utf8(self):
        Entry.register_response('GET snowman', '☃')
        self.assertEqual(self.rclient.get('snowman'), '☃')
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket._requests[0].data, '*2\r\n$3\r\nGET\r\n$7\r\nsnowman\r\n')

    @mocketize
    def test_get_unicode(self):
        Entry.register_response('GET snowman', u'\u2603')
        self.assertEqual(self.rclient.get('snowman'), '☃')
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket.last_request().data, '*2\r\n$3\r\nGET\r\n$7\r\nsnowman\r\n')

    @mocketize
    def test_lrange(self):
        l = ['one', 'two', 'three']
        Entry.register_response('LRANGE list 0 -1', l)
        self.assertEqual(self.rclient.lrange('list', 0, -1), l)
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket.last_request().data, '*4\r\n$6\r\nLRANGE\r\n$4\r\nlist\r\n$1\r\n0\r\n$2\r\n-1\r\n')

    @mocketize
    def test_err(self):
        Entry.register_response('INCRBY counter one', ERROR('ERR value is not an integer or out of range'))
        self.assertRaises(redis.ResponseError, self.rclient.incr, 'counter', 'one')
        self.assertEqual(len(Mocket._requests), 1)
        self.assertEqual(Mocket.last_request().data, '*3\r\n$6\r\nINCRBY\r\n$7\r\ncounter\r\n$3\r\none\r\n')
