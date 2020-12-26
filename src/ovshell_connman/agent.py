import asyncio
from typing import Any, Dict

import urwid

from ovshell import api, widget

from .api import Canceled, ConnmanAgent, ConnmanService


class ConnmanAgentImpl(ConnmanAgent):
    def __init__(self, screen: api.ScreenManager) -> None:
        self.screen = screen

    def report_error(self, service: ConnmanService, error: str) -> None:
        print("ERROR: ", error)

    async def request_input(
        self, service: ConnmanService, fields: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        # {'Passphrase': {'Type': 'psk', 'Requirement': 'mandatory'}}
        # {'Passphrase': {'Type': 'psk', 'Requirement': 'mandatory', 'Alternates': ['WPS']}, 'WPS': {'Type': 'wpspin', 'Requirement': 'alternate'}}

        act = ConnmanInputActivity(self.screen, service, fields)
        modal_opts = api.ModalOptions(
            align="center",
            width=("relative", 60),
            valign="middle",
            height="pack",
            min_width=54,
        )
        self.screen.push_modal(act, modal_opts)
        result = await act.done
        return result

    def cancel(self) -> None:
        pass


class ConnmanInputActivity(api.Activity):
    content: Dict[str, Any]

    def __init__(
        self,
        screen: api.ScreenManager,
        service: ConnmanService,
        fields: Dict[str, Dict[str, Any]],
    ):
        self.screen = screen
        self.service = service
        self.fields = fields
        self.content = {name: None for name, _ in fields.items()}
        self.done: "asyncio.Future[Dict[str, Any]]" = asyncio.Future()

    def create(self) -> urwid.Widget:
        formitems = []

        for name, desc in self.fields.items():
            if desc["Type"] == "psk":
                formitems.append(self._make_field_psk(name, desc))

        formitems.append(urwid.Divider())

        btn_confirm = widget.PlainButton("Confirm")
        urwid.connect_signal(btn_confirm, "click", self._handle_confirm)
        btn_cancel = widget.PlainButton("Cancel")
        urwid.connect_signal(btn_cancel, "click", self._handle_cancel)
        formitems.append(
            urwid.GridFlow([btn_confirm, btn_cancel], 16, 1, 1, urwid.RIGHT)
        )

        form = urwid.Pile(formitems)
        return urwid.LineBox(form, self.service.name)

    def destroy(self) -> None:
        if not self.done.done():
            self.done.set_exception(Canceled())

    def _make_field_psk(self, name: str, desc: Dict[str, Any]) -> urwid.Widget:
        fld = urwid.Edit(multiline=False)
        urwid.connect_signal(fld, "change", self._handle_edit_change, user_args=[name])

        return self._make_field(name, urwid.AttrMap(fld, "edit", "edit"))

    def _make_field(self, title: str, fld: urwid.Widget) -> urwid.Widget:
        return urwid.Pile([urwid.Text(title), fld])

    def _handle_edit_change(self, name: str, w: urwid.Widget, value: str) -> None:
        self.content[name] = value

    def _handle_confirm(self, w: urwid.Widget) -> None:
        self.done.set_result(self.content)
        self.screen.pop_activity()

    def _handle_cancel(self, w: urwid.Widget) -> None:
        self.done.set_exception(Canceled())
        self.screen.pop_activity()
