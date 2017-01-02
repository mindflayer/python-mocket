from tests.test_http import HttpEntryTestCase

from gevent import monkey
monkey.patch_socket()


class GeventHttpEntryTestCase(HttpEntryTestCase):
    pass

