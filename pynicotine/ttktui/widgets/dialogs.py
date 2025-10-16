# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk


class Dialog:

    def __init__(self, parent=None, content_box=None, buttons_box=None, default_widget=None,
                 show_callback=None, close_callback=None, title="", modal=False, width=0, height=0):

        self.parent = parent
        self.content_box = content_box
        self.buttons_box = buttons_box
        self.default_widget = default_widget
        self.show_callback = show_callback
        self.close_callback = close_callback
        self.title = title
        self.modal = modal
        self.default_width = width
        self.default_height = height

        self.window = None

    def present(self):

        if self.window is not None:
            self.close()  # _on_close_request(self.window)

        self.window = ttk.TTkWindow(
            title=self.title,
            size=(min(self.default_width, self.parent.width()), min(self.default_height, self.parent.height()))
        )
        self.window.closed.connect(self._on_close_request)
        self.window.setLayout(ttk.TTkVBoxLayout())

        x = (self.parent.width() // 2) - (self.window.width() // 2)
        y = (self.parent.height() // 2) - (self.window.height() // 2)

        ttk.TTkHelper.overlay(self.parent, self.window, x, y, modal=self.modal)

        if self.content_box:
            self.window.layout().addWidget(self.content_box)

        if self.buttons_box:
            self.window.layout().addWidget(self.buttons_box)

        if self.show_callback:
            self.show_callback(self.window)

        if self.default_widget:
            self.default_widget.setFocus()

    def close(self):
        self.window.close()

    def destroy(self):
        self._on_close_request(self.window)

    @ttk.pyTTkSlot(ttk.TTkWidget)
    def _on_close_request(self, window):

        if window is None:
            return False

        if self.close_callback:
            self.close_callback(window)

        self.window.layout().clear()
        self.window.closed.clear()
        self.window.close()
        self.window = None
        return True


class MessageDialog(ttk.TTkMessageBox):

    def __init__(
        self,
        parent=None,
        title="",
        message="",
        long_message="",
        buttons=None,
        callback=None,
        callback_data=None,
        icon=ttk.TTkMessageBox.Icon.Information,
        default_button=ttk.TTkMessageBox.StandardButton.Close,
        destructive_button=ttk.TTkMessageBox.StandardButton.Discard,
        **kwargs
    ):

        self.parent = parent
        self.callback = callback
        self.callback_data = callback_data

        if not buttons:
            buttons = [
                (MessageDialog.StandardButton.Close, _("Close"))
            ]

        self.default_focus_widget = None
        standardButtons = sum([button for (button, _label) in buttons])

        super().__init__(
            title=title,
            text=message,
            detailedText=long_message,
            icon=icon,
            defaultButton=default_button,
            standardButtons=MessageDialog.StandardButton.NoButton,  # standardButtons
            layout=ttk.TTkGridLayout(),
            **kwargs
        )

        def _clickedSlot(standard_button):
            @ttk.pyTTkSlot()
            def _clicked():
                self.buttonSelected.emit(standard_button)
            return _clicked

        for button_response, button_label in buttons:
            button = ttk.TTkButton(
                text=button_label, border=True, maxHeight=3,
                addStyle={
                    'default': {'color': ttk.TTkColor.RST + ttk.TTkColor.bg("#800000")},
                    'hover': {'color': ttk.TTkColor.YELLOW + ttk.TTkColor.bg("#C00000") + ttk.TTkColor.BOLD},
                    'focus': {'color': ttk.TTkColor.YELLOW + ttk.TTkColor.bg("#C00000") + ttk.TTkColor.BOLD}
                } if button_response == destructive_button else {}
            )
            button.clicked.connect(_clickedSlot(standardButtons & button_response))
            self._widBtnLayout.addWidget(button)

            if button_response == default_button:
                self.default_focus_widget = button

        self.buttonSelected.connect(self._on_button_selected)

    @ttk.pyTTkSlot(ttk.TTkMessageBox.StandardButton)
    def _on_button_selected(self, button):

        if self.callback and button not in [MessageDialog.StandardButton.Cancel,
                                            MessageDialog.StandardButton.Close,
                                            MessageDialog.StandardButton.No]:
            self.callback(self, button, self.callback_data)

        self.close()

    def present(self):

        w, h = self.layout().minimumSize()
        self.resize(w+2, h+4)

        x = (self.parent.width() // 2) - (self.width() // 2)
        y = (self.parent.height() // 2) - (self.height() // 2)

        ttk.TTkHelper.overlay(self.parent, self, x, y, modal=True)

        if self.default_focus_widget:
            self.default_focus_widget.setFocus()


class OptionDialog(MessageDialog):

    def __init__(self, *args, option_label="", option_value=False, icon=ttk.TTkMessageBox.Icon.Question,
                 buttons=None, default_button=ttk.TTkMessageBox.StandardButton.No, **kwargs):

        if not buttons:
            buttons = [
                (MessageDialog.StandardButton.No, _("_No")),
                (MessageDialog.StandardButton.Yes, _("_Yes"))
            ]

        super().__init__(*args, buttons=buttons, default_button=default_button, icon=icon, **kwargs)
