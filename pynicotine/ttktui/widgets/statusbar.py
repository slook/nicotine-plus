# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import textwrap

import TermTk as ttk

from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.widgets.theme import USER_STATUS_COLORS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS


class StatusBar(ttk.TTkContainer):

    def __init__(self, screen, **kwargs) -> None:
        super().__init__(minHeight=1, layout=ttk.TTkHBoxLayout())

        self.screen = screen

        self.setFocusPolicy(ttk.TTkK.ClickFocus)

        self.text_label_container = ttk.TTkContainer(parent=self, minWidth=2, paddingLeft=1)
        self.text_label = ttk.TTkLabel(parent=self.text_label_container, maxHeight=1)

        connections_text = f"{0:4d} 🢇🢅"
        self.connections_label = ttk.TTkLabel(
            parent=self, minWidth=4, maxWidth=8, alignment=ttk.TTkK.RIGHT_ALIGN,
            text=(
                ttk.TTkString(connections_text, ttk.TTkColor.RST)
                .setColorAt(len(connections_text) - 2, ttk.TTkColor.fg("#404040"))
                .setColorAt(len(connections_text) - 1, ttk.TTkColor.fg("#404040"))
            )
        )
        self.connections_label.setToolTip(_("Connections"))

        # ⯅⯆ ▼▲ ▽△ ▾▴ ▿▵ ⏬⏫ ⏷⏶ ⏬⏫ ∇∆ 🠉🠋   🠛🠝  🠯🠭  🠹🠻  🡃🡁  🡇🡅  🡳🡱  🢃🢁  🢇🢅  🢗🢕  ⮉⮋  ⮝⮟  🞃🞁
        download_status_text = f"{0:5d} KiB/s 🡳"
        self.download_status_label = ttk.TTkLabel(
            parent=self, minWidth=16, maxWidth=17, alignment=ttk.TTkK.RIGHT_ALIGN,
            text=(
                ttk.TTkString(download_status_text, ttk.TTkColor.RST)
                .setColorAt(len(download_status_text) - 1, ttk.TTkColor.fg("#606060"))
            )
        )  # ⇩⇓ ↧↡↓⇣⇟ 🮦🭭🮧🭯🮚
        self.download_status_label.setToolTip("Downloading Speed")

        upload_status_text = f"{0:5d} KiB/s 🡱"
        self.upload_status_label = ttk.TTkLabel(
            parent=self, minWidth=16, maxWidth=16, alignment=ttk.TTkK.RIGHT_ALIGN,
            text=(
                ttk.TTkString(upload_status_text, ttk.TTkColor.RST)
                .setColorAt(len(upload_status_text) - 1, ttk.TTkColor.fg("#606060"))
            )
        )  # ⇬⇯⇮⇧⇑⇪↥↟↑⇡⇞ 🮧🭯🮦🭭🮚   🭭🮷🮵🮶🮸 🭯   🮦🭮🮵🮶🭬🮧
        self.upload_status_label.setToolTip("Uploading Speed")

        _spacer2 = ttk.TTkSpacer(parent=self, minWidth=1, maxWidth=2)
        _spacer2 = ttk.TTkSpacer(parent=self, minWidth=1, maxWidth=2)

        self.user_status_button = ttk.TTkButton(
            parent=self, checkable=False, minWidth=12, maxWidth=14,
            text=ttk.TTkString(USER_STATUS_LABELS[UserStatus.OFFLINE].upper(), ttk.TTkColor.BOLD), addStyle={
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
            }
        )
        # self.user_status_button.setFocusPolicy(ttk.TTkK.FocusPolicy.StrongFocus)

        self._text = _("Getting status")
        self._text_wrapper = textwrap.TextWrapper(width=self.text_label_container.width(), max_lines=1, placeholder='…')
        self._tooltip_wrapper = textwrap.TextWrapper(width=self.width(), replace_whitespace=False)

        self.text_label_container.sizeChanged.connect(self.on_resize_status_bar)

    def destroy(self):
        self.text_label_container.sizeChanged.disconnect(self.on_resize_status_bar)
        self.user_status_button.clicked.disconnect(self.screen.on_toggle_status)
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

    def setText(self, text):

        self._text = text

        self.text_label.setText(self._text_wrapper.fill(' '.join(text.strip().split())))  # shorten()
        self.setToolTip(text)

    def setToolTip(self, text):

        if not self._tooltip_wrapper.width or len(text) < self._text_wrapper.width:
            self.text_label.setToolTip("")
            return

        self.text_label.setToolTip(self._tooltip_wrapper.fill(text))
