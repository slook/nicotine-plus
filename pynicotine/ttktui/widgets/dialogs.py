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
            size=(
                min(self.default_width, self.parent.width()),
                min(self.default_height, self.parent.height())
            )
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

        self.default_widget = None
        #standardButtons = sum([button for (button, _label) in buttons])

        super().__init__(
            title=title,
            text=message,
            detailedText=long_message,
            icon=icon,
            defaultButton=default_button,
            standardButtons=MessageDialog.StandardButton.NoButton,  # no standardButtons
            #layout=ttk.TTkGridLayout(),
            **kwargs
        )

        def _clickedSlot(standard_button):
            @ttk.pyTTkSlot()
            def _clicked():
                self.buttonSelected.emit(standard_button)
            return _clicked

        label_width = 0
        for _button_response, button_label in buttons:
            label_width = max(len(button_label), label_width)

        for button_response, button_label in buttons:
            button = ttk.TTkButton(
                text=button_label.center(label_width+2), border=True, maxHeight=3,  # minWidth=len(button_label)+2,
                addStyle={
                    'default': {'color': ttk.TTkColor.RST + ttk.TTkColor.bg("#800000")},
                    'hover': {'color': ttk.TTkColor.YELLOW + ttk.TTkColor.bg("#C00000")},
                    'focus': {'color': ttk.TTkColor.YELLOW + ttk.TTkColor.bg("#C00000")}
                } if button_response == destructive_button else {}
            )
            button.clicked.connect(_clickedSlot(button_response))
            self._widBtnLayout.addWidget(button)

            if button_response == default_button:
                self.default_widget = button

        self.buttonSelected.connect(self._on_button_selected)

    @ttk.pyTTkSlot(ttk.TTkMessageBox.StandardButton)
    def _on_button_selected(self, button):

        self.close()

        if self.callback and button not in [MessageDialog.StandardButton.Cancel,
                                            MessageDialog.StandardButton.Close,
                                            MessageDialog.StandardButton.No]:
            self.callback(self, button, self.callback_data)

    def present(self):

        w, h = self.layout().minimumSize()
        self.resize(w + 2, h + 4)

        x = (self.parent.width() // 2) - (self.width() // 2)
        y = (self.parent.height() // 2) - (self.height() // 2)

        ttk.TTkHelper.overlay(self.parent, self, x, y, modal=True)

        if self.default_widget:
            self.default_widget.setFocus()


class OptionDialog(MessageDialog):

    def __init__(self, *args, option_label="", option_value=False, icon=ttk.TTkMessageBox.Icon.Question,
                 buttons=None, default_button=ttk.TTkMessageBox.StandardButton.No, **kwargs):

        if not buttons:
            buttons = [
                (MessageDialog.StandardButton.No, _("_No")),
                (MessageDialog.StandardButton.Yes, _("_Yes"))
            ]

        super().__init__(*args, buttons=buttons, default_button=default_button, icon=icon, **kwargs)

        self.options = {}
        self.toggle = None

        if option_label:
            self.options["toggle_one"] = self.default_widget = self._add_option_toggle(option_label, option_value)

    def _add_option_toggle(self, option_label, option_value):

        box = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), paddingTop=1, paddingBottom=1)
        box.layout().addWidget(ttk.TTkSpacer())

        toggle = ttk.TTkCheckbox(parent=box, text=option_label, checked=option_value)

        box.layout().addWidget(ttk.TTkSpacer())
        self._widContentLayout.addWidget(box)  # ,3,1,1,3)

        return toggle

    def get_option_value(self, name="toggle_one"):

        if name in self.options:
            return self.options[name].isChecked()

        return None


class EntryDialog(OptionDialog):

    def __init__(self, *args, default="", use_second_entry=False, second_entry_editable=True,
                 second_default="", action_button_label=_("_OK"), droplist=None, second_droplist=None,
                 password=False, multiline=False, **kwargs):

        super().__init__(*args, buttons=[
            (MessageDialog.StandardButton.Cancel, _("_Cancel")),
            (MessageDialog.StandardButton.Ok, action_button_label)
        ], **kwargs)

        self.entry_container = ttk.TTkContainer(layout=ttk.TTkVBoxLayout(), paddingLeft=8, paddingRight=6)
        self._widContentLayout.addWidget(self.entry_container)  # TODO: above combobox

        for option_name, option_default, option_droplist, option_editable in (
            ("entry_one", default, droplist, True),
            ("entry_two", second_default, second_droplist, second_entry_editable)
        ):
            self.options[option_name] = self.add_entry(
                default=option_default,
                droplist=option_droplist,
                echoMode=ttk.TTkLineEdit.EchoMode.Password if password else ttk.TTkLineEdit.EchoMode.Normal,
                editable=option_editable,
                #multiLine=multiline,
                #activates_default=(not use_second_entry),
                name=option_name
            )
            if not use_second_entry:
                break

    def add_entry(self, default="", droplist=None, echoMode=None, editable=True, multiLine=False, name=""):

        @ttk.pyTTkSlot()  # returnPressed
        def return_action():
            entry.clearFocus()  # hide cursor
            self.buttonSelected.emit(MessageDialog.StandardButton.Ok)

        box = ttk.TTkContainer(parent=self.entry_container, layout=ttk.TTkHBoxLayout(), paddingBottom=1)

        if multiLine:
            pass  ## TTkTextEdit not implemented
        if not editable or bool(droplist):
            entry = ttk.TTkComboBox(parent=box, list=droplist, editable=editable, insertPolicy=ttk.TTkK.NoInsert)
            entry.setCurrentText(default)
            #entry.setEditable(editable)
        else:
            entry = ttk.TTkLineEdit(parent=box, echoMode=echoMode, name=name)
            entry.setText(default)
            entry.returnPressed.connect(return_action)  # if not bool(self.options) else return_focus)

        if not self.options:
            self.default_widget = entry

        #self.entry_container.layout().addWidget(box)
        return entry

    def get_entry_value(self, name="entry_one"):

        if name not in self.options:  # entry = self.entry_container.getWidgetByName(name) ; if entry is None: return
            pass  # return None

        if isinstance(self.options[name], ttk.TTkComboBox):
            return str(self.options[name].currentText())

        return str(self.options[name].text())

    def get_second_entry_value(self):
        return self.get_entry_value(name="entry_two")
