import asyncio
from typing import Callable, List

import pytest
import urwid

from ovshell import testing
from ovshell_core.opkg import InstalledPackage, OpkgTools, UpgradablePackage
from ovshell_core.upgradeapp import CheckForUpdatesActivity, PackageSelectionWidget
from ovshell_core.upgradeapp import SystemUpgradeApp
from tests.fixtures.urwid import UrwidMock


class OpkgToolsStub(OpkgTools):
    opkg_binary = "echo"
    _upgradables: List[UpgradablePackage]

    def __init__(self, upgradables: List[UpgradablePackage] = None) -> None:
        self._upgradables = upgradables or []

    async def list_upgradables(self) -> List[UpgradablePackage]:
        return self._upgradables

    async def list_installed(self) -> List[InstalledPackage]:
        return []

    def stub_set_upgradables(self, upgradables: List[UpgradablePackage]) -> None:
        self._upgradables = upgradables

    def get_opkg_binary(self) -> str:
        return self.opkg_binary


def test_app_start(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    app = SystemUpgradeApp(ovshell)

    # WHEN
    app.launch()

    # THEN
    act = ovshell.screen.stub_top_activity()
    assert isinstance(act, CheckForUpdatesActivity)


def test_activity_initial_view(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    act = CheckForUpdatesActivity(ovshell, OpkgToolsStub())

    # WHEN
    wdg = act.create()
    view = urwid_mock.render(wdg)

    # THEN
    assert "System update" in view


@pytest.mark.asyncio
async def test_activity_no_updates(ovshell: testing.OpenVarioShellStub) -> None:
    urwid_mock = UrwidMock()
    act = CheckForUpdatesActivity(ovshell, OpkgToolsStub())
    ovshell.screen.push_activity(act)
    wdg = act.create()

    # First render starts the command
    view = urwid_mock.render(wdg)
    assert "System update" in view
    assert "Checking for updates..." in view

    # Second render shows the output
    await asyncio.sleep(0.1)
    view = urwid_mock.render(wdg)
    assert "Checking for updates..." in view

    # Fourth render renders the finished command
    view = urwid_mock.render(wdg)
    await ovshell.screen.stub_wait_for_tasks(act)
    view = urwid_mock.render(wdg)
    assert "No updates found" in view

    assert "Exit" in view
    urwid_mock.keypress(wdg, ["enter"])
    assert ovshell.screen.stub_top_activity() is None


@pytest.mark.asyncio
async def test_full_upgrade(ovshell: testing.OpenVarioShellStub) -> None:
    urwid_mock = UrwidMock()
    opkgstub = OpkgToolsStub(
        [
            UpgradablePackage("package-one", "1", "1.1"),
            UpgradablePackage("package-two", "2.4", "4.3"),
        ]
    )
    act = CheckForUpdatesActivity(ovshell, opkgstub)
    ovshell.screen.push_activity(act)
    wdg = act.create()

    view = await _until(wdg, lambda v: "upgradable packages found" in v)
    assert "2  upgradable packages found" in view
    assert "Continue" in view

    urwid_mock.keypress(wdg, ["enter"])
    view = urwid_mock.render(wdg)
    assert "[ ] package-one                    1            1.1" in view
    assert "[ ] package-two                    2.4          4.3" in view

    # Press select all
    urwid_mock.keypress(wdg, ["enter"])
    view = urwid_mock.render(wdg)
    assert "[X] package-one" in view
    assert "[X] package-two" in view

    # Press "Upgrade"
    urwid_mock.keypress(wdg, ["right", "enter"])

    view = urwid_mock.render(wdg)
    assert "Upgrading packages..." in view

    view = await _until(wdg, lambda v: "Upgrade completed!" in v)
    assert "Exit" in view

    # Press Exit
    urwid_mock.keypress(wdg, ["enter"])
    assert ovshell.screen.stub_top_activity() is None


@pytest.mark.asyncio
async def test_PackageSelectionWidget_nothing_selected(
    ovshell: testing.OpenVarioShellStub,
) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    packages = [
        UpgradablePackage("package-one", "1", "1.1"),
        UpgradablePackage("package-two", "2.4", "4.3"),
    ]

    wdg = PackageSelectionWidget(packages, ovshell.screen)
    assert "Upgrade" in urwid_mock.render(wdg)

    # WHEN
    # Press "Upgrade" button without selecting anything
    urwid_mock.keypress(wdg, ["right", "enter"])

    # THEN
    dialog = ovshell.screen.stub_dialog()
    assert dialog is not None
    assert dialog.title == "Nothing to upgrade"
    assert dialog.content.text == "Please select one or more packages to upgrade."


def test_PackageSelectionWidget_select_some(
    ovshell: testing.OpenVarioShellStub,
) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    packages = [
        UpgradablePackage("package-one", "1", "1.1"),
        UpgradablePackage("package-two", "2.4", "4.3"),
    ]
    wdg = PackageSelectionWidget(packages, ovshell.screen)

    # WHEN
    # select and deselect package-one, then select package-two
    urwid_mock.keypress(wdg, ["down", "enter", "enter", "down", "enter"])

    # THEN
    view = urwid_mock.render(wdg)
    assert "[ ] package-one" in view
    assert "[X] package-two" in view
    assert wdg.selected == {"package-two"}


async def _until(
    wdg: urwid.Widget, predicate: Callable[[str], bool], timeout: float = 0.05
) -> str:
    urwid_mock = UrwidMock()
    step = 0.01
    view = urwid_mock.render(wdg)
    time = timeout
    while not predicate(view):
        await asyncio.sleep(step)
        time -= step
        if time < 0:
            raise TimeoutError()
        view = urwid_mock.render(wdg)
    return view
