class SuperFakeSSLContext:
    """For Python 3.6 and newer."""

    class FakeSetter(int):
        def __set__(self, *args):
            pass

    minimum_version = FakeSetter()
    options = FakeSetter()
    verify_mode = FakeSetter()
    verify_flags = FakeSetter()


class FakeSSLContext(SuperFakeSSLContext):
    DUMMY_METHODS = (
        "load_default_certs",
        "load_verify_locations",
        "set_alpn_protocols",
        "set_ciphers",
        "set_default_verify_paths",
    )
    sock = None
    post_handshake_auth = None
    _check_hostname = False

    @property
    def check_hostname(self):
        return self._check_hostname

    @check_hostname.setter
    def check_hostname(self, _):
        self._check_hostname = False

    def __init__(self, *args, **kwargs):
        self._set_dummy_methods()

    def _set_dummy_methods(self):
        def dummy_method(*args, **kwargs):
            pass

        for m in self.DUMMY_METHODS:
            setattr(self, m, dummy_method)

    @staticmethod
    def wrap_socket(sock, *args, **kwargs):
        sock.kwargs = kwargs
        sock._secure_socket = True
        return sock

    @staticmethod
    def wrap_bio(incoming, outcoming, *args, **kwargs):
        from mocket.mocket import MocketSocket

        ssl_obj = MocketSocket()
        ssl_obj._host = kwargs["server_hostname"]
        return ssl_obj
