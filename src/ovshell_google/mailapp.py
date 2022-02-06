import asyncio
import time

import qrcode
import urwid

from ovshell import api, widget
from ovshell.api import OpenVarioShell

from .api import GoogleOAuth2, OAuth2DeviceCode
from .oauth2 import GoogleOAuth2Impl


class GoogleMailerApp(api.App):
    name = "email-logs"
    title = "Email Logs"
    description = "Send flight logs via email"
    priority = 50

    def __init__(self, shell: OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        # xcsdir = self.shell.os.path(self.shell.settings.getstrict("xcsoar.home", str))

        act = GoogleMailerActivity(self.shell)
        self.shell.screen.push_activity(act)


class GoogleMailerActivity(api.Activity):
    def __init__(
        self,
        shell: OpenVarioShell,
    ) -> None:
        self.shell = shell

    def create(self) -> urwid.Widget:
        _app_view = self._create_app_view()

        self.frame = urwid.Frame(_app_view, header=widget.ActivityHeader("Email Logs"))
        return self.frame

    def activate(self) -> None:
        act = GoogleOauth2Activity(self.shell, GoogleOAuth2Impl())
        self.shell.screen.push_activity(act)

    def _create_app_view(self) -> urwid.Widget:
        return urwid.Pile(
            [
                urwid.Filler(urwid.Text("Hello World", "center"), "middle"),
            ]
        )


class GoogleOauth2Activity(api.Activity):
    def __init__(self, shell: OpenVarioShell, auth: GoogleOAuth2) -> None:
        self.shell = shell
        self.auth = auth

    def activate(self) -> None:
        self.shell.screen.spawn_task(self, self._get_device_code())

    def create(self) -> urwid.Widget:
        _app_view = self._create_initial_view()

        self.frame = urwid.Frame(
            _app_view, header=widget.ActivityHeader("Connect your Google account")
        )
        # self.frame = urwid.Frame(_app_view)
        # self.shell.screen._mainloop.widget = self.frame
        return self.frame

    async def _get_device_code(self) -> None:
        self.device_code = await self.auth.request_code()
        self.code_timeout = int(time.time()) + self.device_code.expires_in
        time_left = self.device_code.expires_in

        view = self._create_app_view()
        self.frame.set_body(view)

        while time_left > 0:
            print("SLEEPING...")
            await asyncio.sleep(1)
            print("CHECKING...")
            time_left = self.code_timeout - int(time.time())
            self.wait_timeout.set_completion(time_left)
            if time_left % self.device_code.interval == 0:
                token = await self.auth.get_token(self.device_code.device_code)
                if token is not None:
                    return

    def _create_initial_view(self) -> urwid.Widget:
        return urwid.Filler(
            urwid.Padding(urwid.Text("Connecting..."), width="pack", align="center")
        )

    def _create_app_view(self) -> urwid.Widget:
        # self.device_code = OAuth2DeviceCode(
        #     device_code="CXSD-DSAS",
        #     user_code="xxxx",
        #     expires_in=1800,
        #     interval=5,
        #     verification_url="https://www.google.com/device",
        # )

        url_text = urwid.Text(("highlight", self.device_code.verification_url))
        qr_btn = widget.PlainButton(" Show QR Code ")
        urwid.connect_signal(qr_btn, "click", self._on_show_qr)

        self.wait_timeout = urwid.ProgressBar(
            "pg inverted",
            "pg complete",
            current=self.device_code.expires_in,
            done=self.device_code.expires_in,
        )

        pile = urwid.Pile(
            [
                ("pack", urwid.Text("Please visit this URL on your phone:")),
                ("pack", urwid.Divider()),
                (
                    "pack",
                    urwid.Columns(
                        [("pack", url_text), ("pack", qr_btn)],
                        dividechars=1,
                    ),
                ),
                ("pack", urwid.Divider()),
                ("pack", urwid.Text("And enter this code:")),
                (
                    "pack",
                    urwid.Padding(
                        urwid.LineBox(
                            urwid.Text(
                                [
                                    "  ",
                                    ("highlight", self.device_code.user_code),
                                    "  ",
                                ]
                            )
                        ),
                        width="pack",
                        align="center",
                    ),
                ),
                ("pack", urwid.Divider()),
                ("pack", self.wait_timeout),
            ]
        )
        return urwid.Filler(pile, valign="top")

    def _on_show_qr(self, event) -> None:
        # with self.shell.screen.suspended():
        #     breakpoint()

        self._old_hdr = self.frame.get_header()
        self._old_body = self.frame.get_body()

        swidth, sheight = self.shell.screen.get_size()
        portrait = swidth > sheight * 2

        self.frame.set_header(None)
        qr = urwid.Padding(
            AsciiQRCode(self.device_code.verification_url), width="clip", align="center"
        )
        code = urwid.Padding(
            urwid.Text(("highlight", self.device_code.user_code)),
            width="pack",
            align="center",
        )

        if portrait:
            body = urwid.Columns(
                [
                    (54, urwid.Filler(qr)),
                    (len(self.device_code.device_code) + 2, urwid.Filler(code)),
                ]
            )
        else:
            body = urwid.Filler(urwid.Pile([qr, code]))

        signals = widget.KeySignals(body)
        urwid.connect_signal(signals, "cancel", self._on_exit_qr)

        self.frame.set_body(signals)

    def _on_exit_qr(self, event) -> None:
        self.frame.set_header(self._old_hdr)
        self.frame.set_body(self._old_body)
        self._old_hdr = None
        self._old_body = None


class AsciiQRCode(urwid.Widget):
    _sizing = frozenset([urwid.FIXED])
    whitepx = "  "
    blackpx = "██"

    def __init__(self, text: str) -> None:
        self.text = text
        self.qr = qrcode.QRCode(border=1, error_correction=qrcode.ERROR_CORRECT_L)
        self.qr.add_data(text)
        self.qrmatrix = self.qr.get_matrix()

    def pack(self, size=None, focus=False):
        # return sz, sz
        print(len(self.qrmatrix))
        return (len(self.qrmatrix[0]) * 2, len(self.qrmatrix) + 1)
        # return (29, 2)

    def render(self, size, focus=False):
        urwid.widget.fixed_size(size)  # complain if parameter is wrong
        matrix = self.qr.get_matrix()

        markup = []
        for row in matrix:
            markup.extend([self.whitepx if px else self.blackpx for px in row])
            markup.append("\n")

        txt = urwid.Text(markup)
        return txt.render((len(self.qrmatrix[0]) * 2,), focus)
