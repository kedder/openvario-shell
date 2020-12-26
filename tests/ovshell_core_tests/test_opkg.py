import pytest

from ovshell import testing
from ovshell_core.opkg import InstalledPackage, OpkgToolsImpl, UpgradablePackage


class TestOpkgToolsImpl:
    @pytest.mark.asyncio
    async def test_list_upgradables(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        opkg_list_upgradables_out = (
            b"package_one - 1.4.0-r0 - 1.6.1-r0\n" b"package_two - 0.6-r0 - 0.6-r1\n"
        )
        opkgtools = OpkgToolsImpl(ovshell.os, "/bin/echo")
        ovshell.os.stub_expect_run(stdout=opkg_list_upgradables_out)

        # WHEN
        upgradables = await opkgtools.list_upgradables()

        # THEN
        assert upgradables == [
            UpgradablePackage("package_one", "1.4.0-r0", "1.6.1-r0"),
            UpgradablePackage("package_two", "0.6-r0", "0.6-r1"),
        ]

    @pytest.mark.asyncio
    async def test_list_installed(self, ovshell: testing.OpenVarioShellStub) -> None:
        opkg_list_installed_out = (
            b"package-one - 1.4.0-r0\n"
            b"package-two - 0.6-r0\n"
            b"package-three - 201902-r1\n"
        )
        opkgtools = OpkgToolsImpl(ovshell.os, "/bin/echo")
        ovshell.os.stub_expect_run(stdout=opkg_list_installed_out)

        # WHEN
        upgradables = await opkgtools.list_installed()

        # THEN
        assert upgradables == [
            InstalledPackage("package-one", "1.4.0-r0"),
            InstalledPackage("package-two", "0.6-r0"),
            InstalledPackage("package-three", "201902-r1"),
        ]
