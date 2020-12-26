from typing import FrozenSet, List, Set

import urwid

from ovshell import api, widget

from .opkg import OpkgTools, UpgradablePackage, create_opkg_tools


class UnselectableTerminal(urwid.Terminal):
    def selectable(self) -> bool:
        return False

    def keypress(self, size, key):
        return key


class SystemUpgradeApp(api.App):
    name = "system-upgrade"
    title = "Update"
    description = "Check for system updates"
    priority = 20

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        opkg_tools = create_opkg_tools(self.shell.os)
        act = CheckForUpdatesActivity(self.shell, opkg_tools)
        self.shell.screen.push_activity(act)


class CheckForUpdatesActivity(api.Activity):
    check_for_updates_wdg: "CheckForUpdatesWidget"
    select_pkg_wdg: "PackageSelectionWidget"

    def __init__(self, shell: api.OpenVarioShell, opkg_tools: OpkgTools) -> None:
        self.shell = shell
        self.opkg_tools = opkg_tools

    def create(self) -> urwid.Widget:
        ui = CheckForUpdatesWidget(self.opkg_tools, self.shell.screen, self)
        urwid.connect_signal(ui, "continue", self._on_continue)
        urwid.connect_signal(ui, "exit", self._on_exit)
        self.check_for_updates_wdg = ui

        self.content = urwid.WidgetPlaceholder(ui)

        self.frame = urwid.Frame(
            self.content, header=widget.ActivityHeader("System update")
        )
        return self.frame

    def _on_continue(self, wdg: urwid.Widget) -> None:
        upgradables = self.check_for_updates_wdg.upgradables
        ui = PackageSelectionWidget(upgradables, self.shell.screen)
        urwid.connect_signal(ui, "upgrade", self._on_upgrade)
        self.content.original_widget = ui
        self.select_pkg_wdg = ui

    def _on_upgrade(self, wdg: urwid.Widget) -> None:
        packages = self.select_pkg_wdg.selected
        ui = SystemUpgradeWidget(list(packages), self.opkg_tools)
        urwid.connect_signal(ui, "exit", self._on_exit)
        self.content.original_widget = ui

    def _on_exit(self, wdg: urwid.Widget) -> None:
        self.shell.screen.pop_activity()


class CheckForUpdatesWidget(urwid.WidgetWrap):
    signals = ["continue", "exit"]

    upgradables: List[UpgradablePackage]

    def __init__(
        self, opkg_tools: OpkgTools, screen: api.ScreenManager, activity: api.Activity
    ) -> None:
        self.opkg_tools = opkg_tools
        check_for_updates_wdg = self._create_opkg_update_screen()
        self._screen = screen
        self._activity = activity
        super().__init__(check_for_updates_wdg)

    def _create_opkg_update_screen(self) -> urwid.Widget:
        self.message_line = urwid.WidgetPlaceholder(
            urwid.AttrMap(urwid.Text("Checking for updates..."), "progress")
        )

        update_term = urwid.LineBox(
            self._create_update_terminal(), title="opkg update", title_align="left",
        )

        content = urwid.Pile(
            [("pack", self.message_line), ("pack", urwid.Divider()), update_term]
        )
        # Force pack to be selectable, even though no widget is selectable at
        # the moment.
        content._selectable = True
        return content

    def _create_update_terminal(self) -> urwid.Widget:
        cmd = [self.opkg_tools.get_opkg_binary(), "update"]
        self.term = UnselectableTerminal(cmd)
        urwid.connect_signal(self.term, "closed", self._on_opkg_update_finished)
        return urwid.AttrMap(self.term, "bg")

    def _on_opkg_update_finished(self, wdg: urwid.Widget) -> None:
        self._screen.spawn_task(self._activity, self._list_upgradables())

    async def _list_upgradables(self) -> None:
        self.upgradables = await self.opkg_tools.list_upgradables()

        if self.upgradables:
            continue_btn = widget.PlainButton(" Continue ")
            urwid.connect_signal(continue_btn, "click", self._on_continue)
            message = [
                ("success banner", f" {len(self.upgradables)} "),
                ("success message", " upgradable packages found!"),
            ]
            message_wdg = urwid.Columns(
                [("pack", urwid.Text(message)), ("pack", continue_btn)], dividechars=1,
            )
        else:
            exit_btn = widget.PlainButton(" Exit ")
            urwid.connect_signal(exit_btn, "click", self._on_exit)
            message = [("remark", "No updates found")]
            message_wdg = urwid.Columns(
                [("pack", urwid.Text(message)), ("pack", exit_btn)], dividechars=1,
            )

        self.message_line.original_widget = message_wdg

    def _on_continue(self, wdg: urwid.Widget) -> None:
        self._emit("continue")

    def _on_exit(self, wdg: urwid.Widget) -> None:
        self._emit("exit")


class PackageSelectionWidget(urwid.WidgetWrap):
    signals = ["upgrade"]

    selected: Set[str]
    _upgradables: List[UpgradablePackage]

    def __init__(
        self, upgradables: List[UpgradablePackage], screen: api.ScreenManager
    ) -> None:
        self.selected = set()
        self._upgradables = upgradables
        self._screen = screen
        content = self._create_package_list_screen()
        super().__init__(content)

    def sizing(self) -> FrozenSet[str]:
        return frozenset(["box"])

    def _create_package_list_screen(self) -> urwid.Widget:
        self._package_walker = urwid.SimpleFocusListWalker([])
        self._update_packages()

        header = urwid.Columns(
            [
                ("weight", 3, urwid.Text("    Package")),
                ("weight", 1, urwid.Text("From")),
                ("weight", 1, urwid.Text("To")),
            ],
            dividechars=1,
        )

        selector = urwid.Pile(
            [
                ("pack", self._create_buttons()),
                ("pack", urwid.Divider()),
                ("pack", header),
                urwid.ListBox(self._package_walker),
            ]
        )
        return selector

    def _create_buttons(self) -> urwid.Widget:
        btn_select_all = widget.PlainButton("Select All")
        urwid.connect_signal(btn_select_all, "click", self._on_select_all)
        btn_upgrade = widget.PlainButton("Upgrade")
        urwid.connect_signal(btn_upgrade, "click", self._on_upgrade)

        buttons = urwid.GridFlow(
            [btn_select_all, btn_upgrade],
            cell_width=15,
            h_sep=2,
            v_sep=1,
            align="left",
        )

        return buttons

    def _on_select_all(self, wdg: urwid.Widget) -> None:
        self.selected = set(pkg.name for pkg in self._upgradables)
        self._update_packages()

    def _select_package(self, pkgname: str, cb: urwid.CheckBox, state: bool) -> None:
        if state:
            self.selected.add(pkgname)
        else:
            self.selected.discard(pkgname)

    def _on_upgrade(self, wdg: urwid.Widget) -> None:
        if not self.selected:
            msg = urwid.Text("Please select one or more packages to upgrade.")
            self._screen.push_dialog("Nothing to upgrade", msg)
            return
        self._emit("upgrade")

    def _update_packages(self) -> None:
        # Unselect non-upgradable packages
        upgradable_names = [pkg.name for pkg in self._upgradables]
        self.selected.intersection(upgradable_names)

        del self._package_walker[:]

        for pkg in self._upgradables:
            cb = urwid.CheckBox(pkg.name, pkg.name in self.selected)
            urwid.connect_signal(
                cb, "change", self._select_package, user_args=[pkg.name]
            )
            row = urwid.Columns(
                [
                    ("weight", 3, cb),
                    ("weight", 1, urwid.Text(pkg.old_version)),
                    ("weight", 1, urwid.Text(pkg.new_version)),
                ],
                dividechars=1,
            )
            item = urwid.AttrMap(urwid.Padding(row, left=0), "li normal", "li focus")
            self._package_walker.append(item)


class SystemUpgradeWidget(urwid.WidgetWrap):
    signals = ["exit"]
    _packages: List[str]

    def __init__(self, packages: List[str], opkg_tools: OpkgTools) -> None:
        self.opkg_tools = opkg_tools
        self._packages = packages

        content = self._create_upgrade_screen()
        super().__init__(content)

    def _create_upgrade_screen(self) -> urwid.Widget:
        self.message_line = urwid.WidgetPlaceholder(
            urwid.AttrMap(urwid.Text("Upgrading packages..."), "progress")
        )

        update_term = urwid.LineBox(
            self._create_upgrade_terminal(), title="opkg upgrade", title_align="left",
        )

        content = urwid.Pile(
            [("pack", self.message_line), ("pack", urwid.Divider()), update_term]
        )
        # Force pack to be selectable, even though no widget is selectable at
        # the moment.
        content._selectable = True
        return content

    def _create_upgrade_terminal(self) -> urwid.Widget:
        cmd = [self.opkg_tools.get_opkg_binary(), "upgrade"] + self._packages
        self.term = UnselectableTerminal(cmd)
        urwid.connect_signal(self.term, "closed", self._on_opkg_upgrade_finished)
        return urwid.AttrMap(self.term, "bg")

    def _on_opkg_upgrade_finished(self, wdg: urwid.Widget) -> None:
        exit_btn = widget.PlainButton(" Exit ")
        urwid.connect_signal(exit_btn, "click", self._on_exit)
        message = ("success message", "Upgrade completed!")
        message_wdg = urwid.Columns(
            [("pack", urwid.Text(message)), ("pack", exit_btn)], dividechars=1,
        )
        self.message_line.original_widget = message_wdg

    def _on_exit(self, wdg: urwid.Widget) -> None:
        self._emit("exit")
