# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2013 SeeSchloss <see@seos.fr>
# SPDX-FileCopyrightText: 2009-2010 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.widgets.pages import Pages


class UserBrowses(Pages):

    def __init__(self, screen, name="userbrowse"):

        self.screen = screen

        super().__init__(self, name)

        #self.download_dialog = None
        #self.file_properties = None

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        _expander_left = ttk.TTkSpacer(parent=self.header_bar)

        self.userbrowse_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(">", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
        )
        self.userbrowse_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.userbrowse_button.clicked.connect(self.on_userbrowse_clicked)

        self.userbrowse_combobox = ttk.TTkComboBox(parent=self.header_bar, editable=True, insertPolicy=ttk.TTkK.NoInsert)
        self.userbrowse_combobox.lineEdit()._hint = ttk.TTkString(_("Username…"))
        self.userbrowse_combobox.setMinimumWidth(core.users.USERNAME_MAX_LENGTH + 4)
        self.userbrowse_combobox.setMaximumWidth(core.users.USERNAME_MAX_LENGTH + 4)
        self.userbrowse_combobox.currentIndexChanged.connect(self.on_userbrowse_pressed)

        _expander_right = ttk.TTkSpacer(parent=self.header_bar)

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout())
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[name]
        )
        _placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN,
            text=_("Enter the name of a user to browse their shared files, and save the list to disk to inspect it "
                   "later on").replace(", ", ",\n") + "\n\nNOT IMPLEMENTED"
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        for widget in [self.userbrowse_button, self.userbrowse_combobox.lineEdit()]:
            widget.setToolTip(_placeholder.text())

        # Events
        for event_name, callback in (
            #("peer-connection-closed", self.peer_connection_error),
            #("peer-connection-error", self.peer_connection_error),
            ("quit", self.quit),
            #("server-disconnect", self.server_disconnect),
            #("shared-file-list-progress", self.shared_file_list_progress),
            #("shared-file-list-response", self.shared_file_list),
            #("user-browse-remove-user", self.remove_user),
            #("user-browse-show-user", self.show_user),
            #("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def quit(self):
        self.userbrowse_button.clicked.disconnect(self.on_userbrowse_clicked)
        self.userbrowse_combobox.currentIndexChanged.disconnect(self.on_userbrowse_pressed)
        self.userbrowse_combobox.clearFocus()
        self.userbrowse_combobox.close()
        super().destroy()

    def focus_default_widget(self):
        self.userbrowse_combobox.setFocus()

    def on_remove_all_pages(self, *_args):
        core.userbrowse.remove_all_users()

    def on_restore_removed_page(self, page_args):
        username, = page_args
        core.userbrowse.show_user(username)

    @ttk.pyTTkSlot(int)
    def on_switch_page(self, page_number):

        if self.screen.tab_bar.currentWidget() != self:
            return

        self.focus_default_widget()

        page = self.widget(page_number)

        if not page:
            return

        self.remove_tab_changed(page)

    @ttk.pyTTkSlot(int)  # Enter
    def on_userbrowse_pressed(self, _id):
        self.on_get_page(self.userbrowse_combobox)

    @ttk.pyTTkSlot()  # Mouse
    def on_userbrowse_clicked(self):

        if not self.userbrowse_combobox.currentText():
            self.userbrowse_combobox.setFocus()
            return

        self.on_get_page(self.userbrowse_combobox)

    #def on_get_shares(self, *_args):
    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_get_page(self, caller):

        if isinstance(caller, ttk.TTkMenuButton):
            entry_text = caller.data()
        else:
            entry_text = str(caller.currentText()).strip()
            caller.setEditText("")

        if not entry_text:
            return

        if entry_text.startswith("slsk://"):
            core.userbrowse.open_soulseek_url(entry_text)
        else:
            core.userbrowse.browse_user(entry_text)
