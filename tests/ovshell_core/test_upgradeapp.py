from typing import Callable, List, Optional
import asyncio
from dataclasses import dataclass
import mock

import urwid
import pytest

from ovshell import testing
from ovshell_core.upgradeapp import OpkgTools, OpkgToolsImpl, UpgradablePackage
from ovshell_core.upgradeapp import SystemUpgradeApp, CheckForUpdatesActivity
from ovshell_core.upgradeapp import PackageSelectionWidget


class OpkgToolsStub(OpkgTools):
    opkg_binary = "echo"
    _upgradables: List[UpgradablePackage]

    def __init__(self, upgradables: List[UpgradablePackage] = None) -> None:
        self._upgradables = upgradables or []

    def list_upgradables(self) -> List[UpgradablePackage]:
        return self._upgradables

    def stub_set_upgradables(self, upgradables: List[UpgradablePackage]) -> None:
        self._upgradables = upgradables


def test_OpkgToolsImpl_list_upgradables(monkeypatch) -> None:
    # GIVEN
    subpr_mock = mock.Mock(name="subprocess")
    monkeypatch.setattr("ovshell_core.upgradeapp.subprocess", subpr_mock)
    opkgtools = OpkgToolsImpl("echo")

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
    act = CheckForUpdatesActivity(ovshell, OpkgToolsStub())

    # WHEN
    wdg = act.create()
    view = _render(wdg)

    # THEN
    assert "System update" in view


@pytest.mark.asyncio
async def test_activity_no_updates(ovshell: testing.OpenVarioShellStub) -> None:
    act = CheckForUpdatesActivity(ovshell, OpkgToolsStub())
    ovshell.screen.push_activity(act)
    wdg = act.create()

    # First render starts the command
    view = _render(wdg)
    assert "System update" in view
    assert "Checking for updates..." in view

    # Second render shows the output
    await asyncio.sleep(0.1)
    view = _render(wdg)
    assert "Checking for updates..." in view

    # Fourth render renders the finished command
    # await asyncio.sleep(0.1)
    view = _render(wdg)
    view = _render(wdg)
    assert "No updates found" in view

    assert "Exit" in view
    _keypress(wdg, ["enter"])
    assert ovshell.screen.stub_top_activity() is None


@pytest.mark.asyncio
async def test_full_upgrade(ovshell: testing.OpenVarioShellStub) -> None:
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

    _keypress(wdg, ["enter"])
    view = _render(wdg)
    assert "[ ] package-one                    1            1.1" in view
    assert "[ ] package-two                    2.4          4.3" in view

    # Press select all
    _keypress(wdg, ["enter"])
    view = _render(wdg)
    assert "[X] package-one" in view
    assert "[X] package-two" in view

    # Press "Upgrade"
    _keypress(wdg, ["right", "enter"])

    view = _render(wdg)
    assert "Upgrading packages..." in view

    view = await _until(wdg, lambda v: "Upgrade completed!" in v)
    assert "Exit" in view

    # Press Exit
    _keypress(wdg, ["enter"])
    assert ovshell.screen.stub_top_activity() is None


@pytest.mark.asyncio
async def test_PackageSelectionWidget_nothing_selected(
    ovshell: testing.OpenVarioShellStub,
) -> None:
    # GIVEN
    packages = [
        UpgradablePackage("package-one", "1", "1.1"),
        UpgradablePackage("package-two", "2.4", "4.3"),
    ]

    wdg = PackageSelectionWidget(packages, ovshell.screen)
    assert "Upgrade" in _render(wdg)

    # WHEN
    # Press "Upgrade" button without selecting anything
    _keypress(wdg, ["right", "enter"])

    # THEN
    dialog = ovshell.screen.stub_dialog()
    assert dialog is not None
    assert dialog.title == "Nothing to upgrade"
    assert dialog.content.text == "Please select one or more packages to upgrade."


def test_PackageSelectionWidget_select_some(
    ovshell: testing.OpenVarioShellStub,
) -> None:
    # GIVEN
    packages = [
        UpgradablePackage("package-one", "1", "1.1"),
        UpgradablePackage("package-two", "2.4", "4.3"),
    ]
    wdg = PackageSelectionWidget(packages, ovshell.screen)

    # WHEN
    # select and deselect package-one, then select package-two
    _keypress(wdg, ["down", "enter", "enter", "down", "enter"])

    # THEN
    view = _render(wdg)
    assert "[ ] package-one" in view
    assert "[X] package-two" in view
    assert wdg.selected == {"package-two"}


async def _until(
    wdg: urwid.Widget, predicate: Callable[[str], bool], timeout: float = 0.05
) -> str:
    step = 0.01
    view = _render(wdg)
    time = timeout
    while not predicate(view):
        await asyncio.sleep(step)
        time -= step
        if time < 0:
            raise TimeoutError()
        view = _render(wdg)
    return view


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 30))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)


def _keypress(w: urwid.Widget, keys: List[str]) -> None:
    for key in keys:
        nothandled = w.keypress((60, 40), key)
        assert nothandled is None
