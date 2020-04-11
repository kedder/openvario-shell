from typing import Sequence, Tuple, Optional, cast
from typing_extensions import Protocol
from abc import abstractmethod

import urwid

from ovshell.protocol import OpenVarioShell
from ovshell import widget
from ovshell import protocol


class SettingActivator(Protocol):
    @abstractmethod
    def open_value_popup(self, content: urwid.Widget) -> None:
        pass

    @abstractmethod
    def close_value_popup(self) -> None:
        pass


class Setting(Protocol):
    title: str
    value_label: str
    priority: int

    def activate(self, activator: SettingActivator) -> None:
        pass


class StaticChoiceSetting(Setting):
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

    def activate(self, activator: SettingActivator) -> None:
        self._popup_simple_choice(activator)

    def cancelled(self) -> None:
        pass

    def _update(self):
        chdict = dict(self.get_choices())
        self.value = self.read()
        self.value_label = chdict.get(self.value, "N/A")

    def _popup_simple_choice(self, activator: SettingActivator) -> None:
        # Generate choice widget
        menuitems = []
        focus = None
        for key, label in self.get_choices():
            mi = widget.SelectableListItem(label)
            urwid.connect_signal(
                mi, "click", self._choice_clicked, user_args=[activator, key]
            )
            if self.value == key:
                focus = mi
            menuitems.append(mi)

        menu = urwid.Pile(menuitems, focus)

        filler = urwid.Filler(menu, "top")
        box = urwid.LineBox(filler)
        signals = widget.KeySignals(box)
        urwid.connect_signal(
            signals, "cancel", self._choice_cancelled, user_args=[activator]
        )
        activator.open_value_popup(signals)

    def _choice_clicked(
        self, activator: SettingActivator, key: str, w: urwid.Widget
    ) -> None:
        self.store(key)
        self._update()
        activator.close_value_popup()

    def _choice_cancelled(self, activator: SettingActivator, w: urwid.Widget) -> None:
        self.cancelled()
        activator.close_value_popup()


class RotationSetting(StaticChoiceSetting):
    title = "Screen rotation"
    config_key = "core.screen_orientation"
    priority = 80

    def __init__(self, app: protocol.OpenVarioShell):
        self.app = app
        super().__init__()

    def read(self) -> Optional[str]:
        return cast(Optional[str], self.app.settings.get(self.config_key))

    def store(self, value: Optional[str]) -> None:
        self.app.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("0", "Landscape"),
            ("1", "Portrait (90)"),
            ("2", "Landscape (180)"),
            ("3", "Portrait (270)"),
        ]


class LanguageSetting(StaticChoiceSetting):
    title = "Language"
    config_key = "core.language"
    priority = 70

    def __init__(self, app: protocol.OpenVarioShell):
        self.app = app
        super().__init__()

    def read(self) -> Optional[str]:
        return cast(Optional[str], self.app.settings.get(self.config_key))

    def store(self, value: Optional[str]) -> None:
        self.app.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("en_EN.UTF-8", "English"),
            ("de_DE.UTF-8", "German"),
            ("fr_FR.UTF-8", "French"),
            ("ru_RU.UTF-8", "Russian"),
        ]


def get_settings(app: protocol.OpenVarioShell) -> Sequence[Setting]:
    return [RotationSetting(app), LanguageSetting(app)]


class SettingActivatorImpl(SettingActivator):
    def __init__(self, popup_launcher: "SettingsPopUpLauncher"):
        self.popup_launcher = popup_launcher

    def open_value_popup(self, content: urwid.Widget) -> None:
        self.popup_launcher.popup = content
        self.popup_launcher.open_pop_up()

    def close_value_popup(self) -> None:
        self.popup_launcher.close_pop_up()


class SettingRowItem(urwid.WidgetWrap):
    ignore_focus = False

    def __init__(self, setting: Setting) -> None:
        self._setting = setting
        self._title_w = urwid.Text(setting.title)
        self._value_w = urwid.Text(setting.value_label)
        self._value_popup_w = SettingsPopUpLauncher(setting, self._value_w)
        cols = urwid.Columns(
            [("weight", 1, self._title_w), ("weight", 2, self._value_popup_w)]
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

    def __init__(self, setting: Setting, widget: urwid.Widget) -> None:
        super().__init__(widget)
        self.popup = None

    def create_pop_up(self) -> urwid.Widget:
        return self.popup

    def get_pop_up_parameters(self) -> dict:
        return {"left": -1, "top": 1, "overlay_width": 30, "overlay_height": 10}


class SettingsActivity:
    def __init__(self, app: OpenVarioShell) -> None:
        self.app = app

    def create(self) -> urwid.Widget:
        btxt = urwid.BigText("Settings", urwid.font.Thin6x6Font())
        logo = urwid.Padding(btxt, "left", "clip")

        menuitems = []
        for setting in get_settings(self.app):
            menuitems.append(SettingRowItem(setting))

        m_back = widget.SelectableListItem("Back")
        menu = urwid.Pile(menuitems + [urwid.Divider(), m_back])

        view = urwid.Filler(
            urwid.Pile([logo, urwid.Padding(menu, align=urwid.CENTER)]), "top"
        )
        return view

    def activate(self) -> None:
        pass

    def destroy(self) -> None:
        pass
