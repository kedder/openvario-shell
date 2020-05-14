from typing import Sequence, Tuple, Optional, List
from abc import abstractmethod

import urwid

from ovshell import widget
from ovshell import protocol


class StaticChoiceSetting(protocol.Setting):
    title: str
    value: str
    value_label: str

    def __init__(self):
        self._update()

    @abstractmethod
    def read(self) -> Optional[str]:
        pass

    @abstractmethod
    def store(self, value: Optional[str]) -> None:
        pass

    @abstractmethod
    def get_choices(self) -> Sequence[Tuple[str, str]]:
        pass

    def activate(self, activator: protocol.SettingActivator) -> None:
        self._popup_simple_choice(activator)

    def cancelled(self) -> None:
        pass

    def _update(self):
        chdict = dict(self.get_choices())
        self.value = self.read()
        self.value_label = chdict.get(self.value, "N/A")

    def _popup_simple_choice(self, activator: protocol.SettingActivator) -> None:
        # Generate choice widget
        menuitems = []
        focus = None
        choices = self.get_choices()
        height = len(choices)
        width = 0
        for key, label in choices:
            mi = widget.SelectableListItem(label)
            urwid.connect_signal(
                mi, "click", self._choice_clicked, user_args=[activator, key]
            )
            if self.value == key:
                focus = mi
            menuitems.append(mi)

            if len(label) > width:
                width = len(label)

        menu = urwid.Pile(menuitems, focus)

        filler = urwid.Filler(menu, "top")
        box = urwid.LineBox(filler)
        box = urwid.AttrMap(box, widget.LIGHT_ATTR_MAP)

        signals = widget.KeySignals(box)

        urwid.connect_signal(
            signals, "cancel", self._choice_cancelled, user_args=[activator]
        )
        activator.open_value_popup(signals, width + 2, height + 2)

    def _choice_clicked(
        self, activator: protocol.SettingActivator, key: str, w: urwid.Widget
    ) -> None:
        self.store(key)
        self._update()
        activator.close_value_popup()

    def _choice_cancelled(
        self, activator: protocol.SettingActivator, w: urwid.Widget
    ) -> None:
        self.cancelled()
        activator.close_value_popup()


class SettingActivatorImpl(protocol.SettingActivator):
    def __init__(self, popup_launcher: "SettingsPopUpLauncher"):
        self.popup_launcher = popup_launcher

    def open_value_popup(self, content: urwid.Widget, width: int, height: int) -> None:
        self.popup_launcher.set_popup(content, width, height)
        self.popup_launcher.open_pop_up()

    def close_value_popup(self) -> None:
        self.popup_launcher.close_pop_up()


class SettingRowItem(urwid.WidgetWrap):
    def __init__(self, setting: protocol.Setting) -> None:
        self._setting = setting
        self._title_w = urwid.Text(setting.title)
        self._value_w = urwid.Text(setting.value_label)
        self._value_popup_w = SettingsPopUpLauncher(setting, self._value_w)
        cols = urwid.Columns(
            [("weight", 1, self._title_w), ("weight", 1, self._value_popup_w)]
        )
        wdg = urwid.AttrMap(cols, "li normal", "li focus")
        super().__init__(wdg)

    def render(self, size, focus=False):
        self._title_w.set_text(self._setting.title)
        self._value_w.set_text(self._setting.value_label)
        return super().render(size, focus)

    def selectable(self):
        return True

    def keypress(self, size, key: str) -> Optional[str]:
        if self._command_map[key] == "activate":
            activator = SettingActivatorImpl(self._value_popup_w)
            self._setting.activate(activator)
            return None
        return key


class SettingsPopUpLauncher(urwid.PopUpLauncher):
    popup: Optional[urwid.Widget]

    def __init__(self, setting: protocol.Setting, widget: urwid.Widget) -> None:
        super().__init__(widget)
        self.popup = None
        self.popup_width = 20
        self.popup_height = 10

    def set_popup(self, popup: urwid.Widget, width: int, height: int) -> None:
        self.popup = popup
        self.popup_width = width
        self.popup_height = height

    def create_pop_up(self) -> urwid.Widget:
        return self.popup

    def get_pop_up_parameters(self) -> dict:
        return {
            "left": -1,
            "top": 1,
            "overlay_width": self.popup_width,
            "overlay_height": self.popup_height,
        }


class SettingsActivity(protocol.Activity):
    def __init__(self, shell: protocol.OpenVarioShell) -> None:
        self.shell = shell

    def create(self) -> urwid.Widget:
        header = widget.ActivityHeader("Settings")

        menuitems = []
        for setting in self._get_settings():
            menuitems.append(SettingRowItem(setting))

        menu = urwid.Pile(menuitems)

        view = urwid.Filler(
            urwid.Pile([header, urwid.Padding(menu, align=urwid.CENTER)]), "top"
        )
        return view

    def _get_settings(self) -> Sequence[protocol.Setting]:
        settings: List[protocol.Setting] = []
        for ext in self.shell.extensions.list_extensions():
            settings.extend(ext.list_settings())

        return sorted(settings, key=lambda s: -s.priority)
