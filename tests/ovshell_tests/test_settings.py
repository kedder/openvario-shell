import os

from ovshell.settings import StoredSettingsImpl


def test_settings_get() -> None:
    s = StoredSettingsImpl()
    assert s.get("sample", str) is None


def test_settings_setdefault() -> None:
    s = StoredSettingsImpl()
    s.setdefault("sample", 1)
    s.setdefault("list", [1, 2, 3])

    assert s.get("sample", int) == 1
    assert s.get("list", list) == [1, 2, 3]


def test_settings_save_load(tmpdir) -> None:
    conffname = os.path.join(tmpdir, "config")
    s = StoredSettingsImpl({}, filename=conffname)
    s.set("one", "One")
    s.setdefault("two", [2, 2])
    s.set("three", 3, save=True)

    loaded = StoredSettingsImpl.load(conffname)

    assert loaded.get("one", str) == "One"
    assert loaded.get("two", list) == [2, 2]
    assert loaded.get("three", int) == 3


def test_settings_save_load_not_existing(tmpdir) -> None:
    conffname = os.path.join(tmpdir, "config")
    s = StoredSettingsImpl.load(conffname)

    assert s.get("one", str) is None
    assert s.get("three", str) is None

    s.set("three", 3, save=True)

    loaded = StoredSettingsImpl.load(conffname)
    assert loaded.get("three", int) == 3
    assert loaded.get("three", str) is None
