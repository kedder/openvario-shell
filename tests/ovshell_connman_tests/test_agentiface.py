from dbus_next import Variant

from ovshell_connman.agentiface import unpack_variants


def test_unpack_variants() -> None:
    assert unpack_variants("plain") == "plain"

    inp = Variant("i", 5)
    assert unpack_variants(inp) == 5

    inp = Variant("a{sv}", {"one": Variant("i", 1)})
    assert unpack_variants(inp) == {"one": 1}

    inp = Variant("(sv)", ["foo", Variant("u", 5)])
    assert unpack_variants(inp) == ["foo", 5]

    inp = Variant("(asv)", [["foo"], Variant("u", 5)])
    assert unpack_variants(inp) == [["foo"], 5]

    inp = Variant("(avv)", [[Variant("s", "foo")], Variant("u", 5)])
    assert unpack_variants(inp) == [["foo"], 5]

    inp = Variant("aav", [[Variant("s", "foo"), Variant("u", 5)]])
    assert unpack_variants(inp) == [["foo", 5]]
