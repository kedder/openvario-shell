from typing import List

import urwid

from ovshell import testing
from ovshell_core.setupapp import SetupActivity, SetupApp


class TestSetupApp:
    def test_launch(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        app = SetupApp(ovshell)

        # WHEN
        app.launch()

        # THEN
        act = ovshell.screen.stub_top_activity()
        assert isinstance(act, SetupActivity)


class TestSetupActivity:
    def test_wizard_go_through(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        act = SetupActivity(ovshell)
        w = act.create()

        rendered = _render(w)
        assert "Setup wizard" in rendered
        assert "his wizard will guide you through" in rendered
        _keypress(w, ["enter"])

        rendered = _render(w)
        assert "Device orientation" in rendered
        _keypress(w, ["enter"])

        rendered = _render(w)
        assert "Touch screen calibration" in rendered
        _keypress(w, ["enter"])

        rendered = _render(w)
        assert "Sensor calibration" in rendered
        _keypress(w, ["enter"])

        rendered = _render(w)
        assert "Setup is completed" in rendered


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 30))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)


def _keypress(w: urwid.Widget, keys: List[str]) -> None:
    for key in keys:
        nothandled = w.keypress((60, 40), key)
        assert nothandled is None
