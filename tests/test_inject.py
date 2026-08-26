import sys
import types

from mocket import inject


def test_disable_calls_pyopenssl_inject_when_available(monkeypatch):
    calls: list[str] = []
    pyopenssl_module = types.ModuleType("urllib3.contrib.pyopenssl")

    def fake_inject_into_urllib3():
        calls.append("called")

    pyopenssl_module.inject_into_urllib3 = fake_inject_into_urllib3
    monkeypatch.setitem(sys.modules, "urllib3.contrib.pyopenssl", pyopenssl_module)
    monkeypatch.setattr(inject, "_patches_restore", {})
    monkeypatch.setattr(inject, "_enable_depth", 1)

    inject.disable()

    assert calls == ["called"]


def test_enable_calls_pyopenssl_extract_when_available(monkeypatch):
    calls: list[str] = []
    pyopenssl_module = types.ModuleType("urllib3.contrib.pyopenssl")

    def fake_extract_from_urllib3():
        calls.append("called")

    def fake_inject_into_urllib3():
        pass

    pyopenssl_module.extract_from_urllib3 = fake_extract_from_urllib3
    pyopenssl_module.inject_into_urllib3 = fake_inject_into_urllib3
    monkeypatch.setitem(sys.modules, "urllib3.contrib.pyopenssl", pyopenssl_module)
    monkeypatch.setattr(inject, "_patches_restore", {})
    monkeypatch.setattr(inject, "_enable_depth", 0)

    inject.enable()
    inject.disable()

    assert calls == ["called"]
