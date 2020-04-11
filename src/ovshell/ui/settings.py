from typing import Iterable, Sequence, Tuple
from typing_extensions import Protocol
from abc import abstractmethod

import urwid

from ovshell.protocol import OpenVarioShell
from ovshell import widget


class SettingsSimpleChoiceHandler(Protocol):
    def focused(self, key: str) -> None:
        pass

    def selected(self, key: str) -> None:
        pass

    def cancelled(self) -> None:
        pass


class SettingActivator(Protocol):
    @abstractmethod
    def simple_choice(
        self,
        items: Iterable[Tuple[str, str]],
        selected: str,
        choice: SettingsSimpleChoiceHandler,
    ) -> None:
        pass


class Setting(Protocol):
    title: str
    value: str
    priority: int

    def activate(self, activator: SettingActivator) -> None:
        pass


class RotationSetting(Setting, SettingsSimpleChoiceHandler):
    title = "Screen rotation"
    priority = 80

    def __init__(self):
        self.value = "Landscape"

    def activate(self, activator: SettingActivator) -> None:
        choices = [
            ("0", "Landscape"),
            ("1", "Portrait (90)"),
            ("2", "Landscape (180)"),
            ("3", "Portrait (270)"),
        ]
        activator.simple_choice(choices, "0", self)


class LanguageSetting(Setting, SettingsSimpleChoiceHandler):
    title = "Language"
    priority = 70

    def __init__(self):
        self.value = "English"

    def activate(self, activator: SettingActivator) -> None:
        choices = [
            ("en_EN.UTF-8", "English"),
            ("de_DE.UTF-8", "German"),
            ("fr_FR.UTF-8", "French"),
            ("ru_RU.UTF-8", "Russian"),
        ]
        activator.simple_choice(choices, "de_DE.UTF-8", self)


def get_settings() -> Sequence[Setting]:
    return [RotationSetting(), LanguageSetting()]


class SettingActivatorImpl(SettingActivator):
    def __init__(self, popup_launcher: "SettingsPopUpLauncher"):
        self.popup_launcher = popup_launcher

    def simple_choice(
        self,
        items: Iterable[Tuple[str, str]],
        selected: str,
        handler: SettingsSimpleChoiceHandler,
    ) -> None:
        # Generate choice widget
        menuitems = []
        for key, label in items:
            mi = widget.SelectableListItem(label)
            urwid.connect_signal(
                mi, "click", self._simple_choice_clicked, user_args=[handler, key]
            )
            menuitems.append(mi)

        menu = urwid.Pile(menuitems)
        filler = urwid.Filler(menu, "top")
        box = urwid.LineBox(filler)
        self.popup_launcher.popup = box
        self.popup_launcher.open_pop_up()

    def _simple_choice_clicked(
        self, handler: SettingsSimpleChoiceHandler, key: str, w: urwid.Widget
    ) -> None:
        handler.selected(key)


class SettingsActivity:
    def __init__(self, app: OpenVarioShell) -> None:
        self.app = app

    def create(self) -> urwid.Widget:
        btxt = urwid.BigText("Settings", urwid.font.Thin6x6Font())
        logo = urwid.Padding(btxt, "left", "clip")

        menuitems = []
        for setting in get_settings():
            itemlabel = f"{setting.title} ({setting.value})"
            mi = SettingsPopUpLauncher(setting, widget.SelectableListItem(itemlabel))
            urwid.connect_signal(
                mi.original_widget,
                "click",
                self._activate_setting,
                user_args=[setting, mi],
            )
            menuitems.append(mi)
        # m_rot = widget.SelectableListItem("Screen Rotation")
        # m_lang = SettingsPopUpLauncher(self.app, widget.SelectableListItem("Language"))

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

    def _activate_setting(
        self, setting: Setting, mi: "SettingsPopUpLauncher", btn: urwid.Widget
    ):
        activator = SettingActivatorImpl(mi)
        setting.activate(activator)


class SettingsPopUpLauncher(urwid.PopUpLauncher):
    def __init__(self, setting: Setting, widget: urwid.Widget) -> None:
        super().__init__(widget)
        self.popup = None

    def create_pop_up(self) -> urwid.Widget:
        return self.popup

    def get_pop_up_parameters(self) -> dict:
        return {"left": 3, "top": 1, "overlay_width": 50, "overlay_height": 10}
