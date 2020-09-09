import mock


from ovshell import testing
from ovshell_core.opkg import OpkgToolsImpl, UpgradablePackage


class TestOpkgToolsImpl:
    def test_list_upgradables(
        self, ovshell: testing.OpenVarioShellStub, monkeypatch
    ) -> None:
        # GIVEN
        subpr_mock = mock.Mock(name="subprocess")
        monkeypatch.setattr("ovshell_core.opkg.subprocess", subpr_mock)
        opkgtools = OpkgToolsImpl(ovshell.os, "/bin/echo")

        proc_mock = mock.Mock(name="Process")
        proc_mock.returncode = 0
        proc_mock.stdout = (
            b"package_one - 1.4.0-r0 - 1.6.1-r0\n" b"package_two - 0.6-r0 - 0.6-r1\n"
        )
        subpr_mock.run.return_value = proc_mock

        # WHEN
        upgradables = opkgtools.list_upgradables()

        # THEN
        assert upgradables == [
            UpgradablePackage("package_one", "1.4.0-r0", "1.6.1-r0"),
            UpgradablePackage("package_two", "0.6-r0", "0.6-r1"),
        ]
