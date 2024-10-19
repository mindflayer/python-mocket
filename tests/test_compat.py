from mocket.compat import do_the_magic


def test_unknown_binary():
    assert do_the_magic(b"foobar-binary") == "application/octet-stream"
