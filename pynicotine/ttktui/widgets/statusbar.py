# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from textwrap import TextWrapper

from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.widgets.theme import USER_STATUS_COLORS
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS


class StatusBar(ttk.TTkContainer):

    def __init__(self, screen, **kwargs) -> None:
        super().__init__(minHeight=1, layout=ttk.TTkHBoxLayout())

        self.screen = screen

        self._text = _("Getting status")
        self._conns = None

        self._text_wrapper = None
        self._tooltip_wrapper = None

        self.setFocusPolicy(ttk.TTkK.ClickFocus)

        self.text_label_container = ttk.TTkContainer(parent=self, maxHeight=1, minWidth=2, paddingLeft=1)
        self.text_label = None

        _spacer1 = ttk.TTkSpacer(parent=self, minWidth=0, maxWidth=2)

        self.connections_status_container = ttk.TTkContainer(parent=self, maxHeight=1, minWidth=4, maxWidth=8)
        self.connections_label = None

        _spacer2 = ttk.TTkSpacer(parent=self, minWidth=0, maxWidth=1)

        # ⯅⯆ ▼▲ ▽△ ▾▴ ▿▵ ⏬⏫ ⏷⏶ ⏬⏫ ∇∆ 🠉🠋   🠛🠝  🠯🠭  🠹🠻  🡃🡁  🡇🡅  🡳🡱  🢃🢁  🢇🢅  🢗🢕  ⮉⮋  ⮝⮟  🞃🞁
        self.downloads_status_container = ttk.TTkContainer(parent=self, maxHeight=1, minWidth=16, maxWidth=17)
        self.uploads_status_container = ttk.TTkContainer(parent=self, maxHeight=1, minWidth=16, maxWidth=16)

        _spacer3 = ttk.TTkSpacer(parent=self, minWidth=1, maxWidth=2)

        self.user_status_button = None

    def connect_signals(self):

        self._text_wrapper = TextWrapper(width=self.text_label_container.width(), max_lines=1, placeholder='…')
        self._tooltip_wrapper = TextWrapper(width=self.width(), replace_whitespace=False)

        self.text_label = ttk.TTkLabel(text=self._text, parent=self.text_label_container, maxHeight=1)
        self.user_status_button = StatusButton(parent=self)

        self.user_status_button.clicked.connect(self.screen.on_toggle_status)
        self.text_label_container.sizeChanged.connect(self.on_resize_status_bar)

        self.on_resize_status_bar(self.text_label_container.height(), self.text_label_container.width())
        self.set_connection_stats(0, 0, 0)

    def destroy(self):
        self.user_status_button.clicked.disconnect(self.screen.on_toggle_status)
        self.text_label_container.sizeChanged.disconnect(self.on_resize_status_bar)
        self._text_wrapper = self._tooltip_wrapper = None

    def mousePressEvent(self, evt: ttk.TTkMouseEvent):
        if self.screen.log_view.isVisible():
            self.screen.log_view.hide_log()
        else:
            self.screen.log_view.show_log()
        return True

    def wheelEvent(self, evt: ttk.TTkMouseEvent) -> bool:
        if evt.evt == ttk.TTkK.WHEEL_Up:
            if not self.screen.log_view.isVisible():
                self.screen.log_view.show_log()
        else:
            if self.screen.log_view.isVisible():
                self.screen.log_view.hide_log()
        return True

    @ttk.pyTTkSlot(int, int)
    def on_resize_status_bar(self, _w, _h):
        self._text_wrapper.width = max(1, self.text_label_container.width() - 2)
        self._tooltip_wrapper.width = self.width()
        self.setText(self._text)

    def set_connection_stats(self, total_conns, download_bandwidth, upload_bandwidth):

        if total_conns == self._conns:
            return

        self._conns = total_conns

        if self.connections_label is None:
            self.connections_label = ttk.TTkLabel(
                parent=self.connections_status_container, minWidth=4, maxWidth=8, alignment=ttk.TTkK.RIGHT_ALIGN,
            )
            self.connections_label.setToolTip(_("Connections"))

        total_conns_text = f"{repr(total_conns)} 🢇🢅"
        text_color = ttk.TTkColor.BOLD if total_conns else ttk.TTkColor.RST

        if not total_conns:
            rx_color = tx_color = ttk.TTkColor.fg("#404040")  # ttk.TTkColor.STRIKETROUGH

        elif total_conns <= 2:
            rx_color = ttk.TTkColor.MAGENTA
            tx_color = USER_STATUS_COLORS[UserStatus.OFFLINE]

        else:
            rx_color = ttk.TTkColor.GREEN if download_bandwidth else USER_STATUS_COLORS[UserStatus.ONLINE]
            tx_color = ttk.TTkColor.YELLOW if upload_bandwidth else USER_STATUS_COLORS[UserStatus.AWAY]

        self.connections_label.setText(
            ttk.TTkString(total_conns_text, text_color)
            .setColorAt(len(total_conns_text) - 2, rx_color)  # 🢇
            .setColorAt(len(total_conns_text) - 1, tx_color)  # 🢅
        )

    def setText(self, text):

        self._text = text

        self.text_label.setText(self._text_wrapper.fill(' '.join(text.strip().split())))  # shorten()
        self.setToolTip(text)

    def setToolTip(self, text):

        if not self._tooltip_wrapper.width or len(text) < self._text_wrapper.width:
            self.text_label.setToolTip("")
            return

        self.text_label.setToolTip(self._tooltip_wrapper.fill(text))


class StatusButton(ttk.TTkButton):

    def __init__(self, parent=None, **kwargs) -> None:
        super().__init__(
            parent=parent,
            minWidth=12,
            maxWidth=14,
            text=ttk.TTkString(USER_STATUS_LABELS[UserStatus.OFFLINE].upper(), ttk.TTkColor.BOLD),
            addStyle={
                'default': {
                    'color': ttk.TTkColor.WHITE + USER_STATUS_COLORS[UserStatus.OFFLINE].invertFgBg(),
                    'borderColor': ttk.TTkColor.BG_RED + ttk.TTkColor.BLINKING,
                },
                'disabled': {
                    'color': ttk.TTkColor.bg("#888888") + ttk.TTkColor.BLINKING,
                    'borderColor': ttk.TTkColor.fg("#888888"),
                },
                'hover': {
                    'color': ttk.TTkColor.YELLOW + ttk.TTkColor.BG_RED,
                    'borderColor': ttk.TTkColor.RST + ttk.TTkColor.fg("#FFFFCC") + ttk.TTkColor.BLINKING,
                },
                'checked': {
                    'color': ttk.TTkColor.BLACK + USER_STATUS_COLORS[UserStatus.AWAY].invertFgBg(),
                    'borderColor': ttk.TTkColor.BG_YELLOW,
                },
                'unchecked': {
                    'color': ttk.TTkColor.BLACK + USER_STATUS_COLORS[UserStatus.ONLINE].invertFgBg(),
                    'borderColor': ttk.TTkColor.BG_GREEN,
                },
                'clicked': {
                    'color': ttk.TTkColor.fg("#FFFFDD"),
                    'borderColor': ttk.TTkColor.fg("#DDDDDD") + ttk.TTkColor.BOLD,
                },
                'focus': {
                    'color': ttk.TTkColor.fgbg("#dddd88", "#0000AA"),
                    'borderColor': ttk.TTkColor.RST + ttk.TTkColor.fg("#ffff00") + ttk.TTkColor.BLINKING,
                },
            },
            **kwargs,
        )

    def update_status(self, status, username=None):

        status_icon = USER_STATUS_ICONS.get(status)
        status_text = USER_STATUS_LABELS.get(status).upper()

        if username is not None:
            self.setCheckable(True)
            self.setChecked(status == UserStatus.AWAY)
            self.setToolTip(status_icon + ttk.TTkString(username) + " ")

        elif self.isCheckable():
            self.setCheckable(False)
            self.setToolTip("")

        if str(self.text()) != status_text:
            self.setText(ttk.TTkString(status_text, ttk.TTkColor.BOLD))

        self.setEnabled(True)
