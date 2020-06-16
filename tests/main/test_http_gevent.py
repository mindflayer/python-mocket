from gevent import monkey

from tests.main.test_http import HttpEntryTestCase

monkey.patch_socket()


class GeventHttpEntryTestCase(HttpEntryTestCase):
    pass
