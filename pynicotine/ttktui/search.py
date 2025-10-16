# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

#from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.widgets.pages import Pages


class Searches(Pages):

    MODES = {
        "global": _("_Global"),
        "buddies": _("_Buddies"),
        "rooms": _("_Rooms"),
        "user": _("_User")
    }

    def __init__(self, screen, name="search"):

        self.screen = screen

        super().__init__(self, name)

        #self.download_dialog = None
        #self.file_properties = None

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        _expander_left = ttk.TTkSpacer(parent=self.header_bar)

        self.search_mode_combobox = ttk.TTkComboBox(parent=self.header_bar, list=list(self.MODES.values()), index=0)
        self.search_mode_combobox.setMinimumWidth(max(len(m) for m in self.MODES.values()) + 2)
        self.search_mode_combobox.setMaximumWidth(max(len(m) for m in self.MODES.values()) + 4)
        self.search_mode_combobox.currentIndexChanged.connect(self.on_search_mode)

        self.room_search_combobox = ttk.TTkComboBox(parent=self.header_bar, editable=True, insertPolicy=ttk.TTkK.NoInsert, visible=False)
        self.room_search_combobox.lineEdit()._hint = ttk.TTkString(_("Room…"))
        self.room_search_combobox.setMinimumWidth(8)
        self.room_search_combobox.setMaximumWidth(core.chatrooms.ROOM_NAME_MAX_LENGTH + 4)
        self.room_search_combobox.currentIndexChanged.connect(self.focus_default_widget)

        self.user_search_combobox = ttk.TTkComboBox(parent=self.header_bar, editable=True, insertPolicy=ttk.TTkK.NoInsert, visible=False)
        self.user_search_combobox.lineEdit()._hint = ttk.TTkString(_("Username…"))
        self.user_search_combobox.setMinimumWidth(8)
        self.user_search_combobox.setMaximumWidth(core.users.USERNAME_MAX_LENGTH + 4)
        self.user_search_combobox.currentIndexChanged.connect(self.focus_default_widget)

        self.search_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(">", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
        )
        self.search_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.search_button.clicked.connect(self.on_search_clicked)

        self.search_combobox = ttk.TTkComboBox(parent=self.header_bar, editable=True, insertPolicy=ttk.TTkK.NoInsert)
        self.search_combobox.lineEdit()._hint = ttk.TTkString(_("Search term…"))
        self.search_combobox.setMinimumWidth(16)
        #self.search_combobox.setMaximumWidth(40)
        self.search_combobox.currentIndexChanged.connect(self.on_search_pressed)

        _expander_right = ttk.TTkSpacer(parent=self.header_bar)

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout())
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[name]
        )
        _placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN,
            text=_("Enter a search term to search for files shared by other online users") + "\n\nNOT IMPLEMENTED"
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        for widget in [self.search_button, self.search_combobox.lineEdit()]:
            widget.setToolTip(_placeholder.text())

        # Events
        for event_name, callback in (
            #("add-search", self.add_search),
            #("add-wish", self.update_wish_button),
            #("clear-wish-filters", self.update_wish_filters),
            #("file-search-response", self.file_search_response),
            ("quit", self.quit),
            #("remove-search", self.remove_search),
            #("remove-wish", self.update_wish_button),
            #("show-search", self.show_search),
            #("update-wish-filters", self.update_wish_filters)
        ):
            events.connect(event_name, callback)

        #self.populate_search_history()

    def quit(self):
        self.search_button.clicked.disconnect(self.on_search_clicked)
        self.search_combobox.currentIndexChanged.disconnect(self.on_search_pressed)
        self.search_combobox.clearFocus()
        self.search_combobox.close()
        super().destroy()

    def focus_default_widget(self):
        self.search_combobox.setFocus()

    def on_remove_all_pages(self, *_args):
        core.search.remove_all_searches()

    def on_restore_removed_page(self, page_args):
        search_term, mode, room, users = page_args
        core.search.do_search(search_term, mode, room=room, users=users)

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
    def on_search_mode(self, index):

        search_mode = list(self.MODES)[index]

        self.user_search_combobox.setVisible(search_mode == "user")
        self.room_search_combobox.setVisible(search_mode == "rooms")

    @ttk.pyTTkSlot(int)  # Enter
    def on_search_pressed(self, _id):
        self.on_get_page(self.search_combobox)

    @ttk.pyTTkSlot()  # Mouse
    def on_search_clicked(self):

        if not self.search_combobox.currentText():
            self.search_combobox.setFocus()
            return

        self.on_get_page(self.search_combobox)

    #def on_get_shares(self, *_args):
    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_get_page(self, caller):

        if isinstance(caller, ttk.TTkMenuButton):
            text = caller.data()
        else:
            text = str(caller.currentText()).strip()
            caller.setEditText("")

        if not text:
            return

        mode = list(self.MODES)[self.search_mode_combobox.currentIndex()]
        room = self.room_search_combobox.currentText()
        user = self.user_search_combobox.currentText()
        users = [user] if user else []

        if mode == "rooms" and not room:
            return

        core.search.do_search(text, mode, room=room, users=users)
