import urwid


class MainMenuView:
    def create(self) -> urwid.Widget:
        btxt = urwid.BigText("Menu", urwid.font.Thin6x6Font())
        splash = urwid.Filler(urwid.Padding(btxt, "center", "clip"), "middle")
        return splash

    def activate(self) -> None:
        pass

    def destroy(self) -> None:
        pass
