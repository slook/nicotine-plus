# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2009 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import time

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.widgets.popupmenu import UserPopupMenu
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS
from pynicotine.utils import UINT64_LIMIT
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class Buddies(ttk.TTkTree):

    def __init__(self, screen, name="userlist"):
        super().__init__(name=name)

        self.screen = screen

        self.header = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        self.header.layout().addWidget(ttk.TTkSpacer())

        self.entry_button = ttk.TTkButton(
            parent=self.header,
            text=ttk.TTkString("+", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5
        )
        self.entry_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.entry_button.clicked.connect(self.on_entry_clicked)

        self.add_buddy_entry = ttk.TTkLineEdit(
            parent=self.header,
            hint=_("Add buddy…")
        )
        self.add_buddy_entry.setMinimumWidth(30)
        self.add_buddy_entry.setMaximumWidth(30)
        self.add_buddy_entry.returnPressed.connect(self.on_entry_pressed)

        self.header.layout().addWidget(ttk.TTkSpacer())

        tooltip = _("Add users as buddies to share specific folders with them and receive notifications when they are online")
        for widget in [self.entry_button, self.add_buddy_entry]:
            widget.setToolTip(tooltip)

        # Rows
        self.buddy_items = {}

        # Columns
        self.setHeaderLabels([
            " ",               # 0 0
            _("User"),         # 2 1
            _("Country"),      # 1 2
            _("Speed"),        # 3 3
            _("Files"),        # 4 4
            _("Trusted"),      # 5 5
            _("Notify"),       # 6 6
            _("Prioritized"),  # 7 7
            _("Last Seen"),    # 8 8
            _("Note"),         # 9 9
            # "10",
            # "11",
            # "12"
        ])

        for col, width in enumerate([3, 30, 7, 12, 8, 8, 8, 12, 20, 40]):
            self.setColumnWidth(col, width)

        self.popup_menu = None

        # Events
        for event_name, callback in (
            ("add-buddy", self.add_buddy),
            #("buddy-note", self.buddy_note),
            ("buddy-notify", self.buddy_notify),
            ("buddy-last-seen", self.buddy_last_seen),
            ("buddy-prioritized", self.buddy_prioritized),
            ("buddy-trusted", self.buddy_trusted),
            ("remove-buddy", self.remove_buddy),
            ("server-disconnect", self.server_disconnect),
            ("start", self.start),
            ("user-country", self.user_country),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def connect_signals(self):
        self.screen.tab_bar.currentChanged.connect(self.on_focus_tab)

    def start(self):

        #comboboxes = (
        #    self.window.search.user_search_combobox,
        #    self.window.userbrowse.userbrowse_combobox,
        #    self.window.userinfo.userinfo_combobox
        #)

        for username, user_data in core.buddies.users.items():
            self.add_buddy(username, user_data, select_row=False)

        self._treeView.setSortingEnabled(True)
        self.sortItems(1, ttk.TTkK.AscendingOrder)  # User

    @ttk.pyTTkSlot(int)
    def on_focus_tab(self, _tab_number):
        if self.screen.tab_bar.currentWidget() == self:
            self.screen.setWidget(widget=self.header, position=self.screen.HEADER)
            self.add_buddy_entry.setFocus()

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def set_buddy_list_position(self, button):

        if button.isChecked():
            config.sections["ui"]["modes_visible"]["userlist"] = False
            config.sections["ui"]["buddylistinchatrooms"] = "always"

            self.screen.hide_tab("userlist")
            self.screen.side_bar.setVisible(True)

            #self.screen.setWidget(widget=self, position=self.screen.RIGHT, size=35)

        else:
            config.sections["ui"]["modes_visible"]["userlist"] = True
            config.sections["ui"]["buddylistinchatrooms"] = "tab"
            self.screen.side_bar.setVisible(False)

            #self.screen.layout().removeWidget(widget=self)  # , position=self.screen.RIGHT)

            self.screen.append_main_tabs()

    @ttk.pyTTkSlot()  # Enter
    def on_entry_pressed(self):
        self.on_add_buddy(self.add_buddy_entry)

    @ttk.pyTTkSlot()  # Mouse
    def on_entry_clicked(self):

        if not self.add_buddy_entry.text():
            self.add_buddy_entry.setFocus()
            return

        self.on_add_buddy(self.add_buddy_entry)

    def on_add_buddy(self, *_args):

        username = self.add_buddy_entry.text().toAscii().strip()

        if not username:
            return

        self.add_buddy_entry.setText("")
        core.buddies.add_buddy(username)
        self.setFocus()

    def add_buddy(self, user, user_data, select_row=True):

        status = user_data.status
        country_code = user_data.country

        if country_code:
            country_code = country_code.replace("flag_", "")

        stats = core.users.watched.get(user)

        if stats is not None:
            speed = stats.upload_speed or 0
            files = stats.files
        else:
            speed = 0
            files = None

        h_speed = human_speed(speed) if speed > 0 else ""
        h_files = humanize(files) if files is not None else ""
        last_seen = UINT64_LIMIT
        h_last_seen = ""

        if user_data.last_seen:
            try:
                last_seen_time = time.strptime(user_data.last_seen, "%m/%d/%Y %H:%M:%S")
                last_seen = time.mktime(last_seen_time)
                h_last_seen = time.strftime("%x %X", last_seen_time)

            except ValueError:
                last_seen = 0
                h_last_seen = _("Never seen")

        self.buddy_items[user] = buddy_item = Buddy([
            USER_STATUS_LABELS.get(status, ""),
            str(user),
            country_code,  # get_flag_icon_name(country_code),
            str(h_speed),
            str(h_files),
            ttk.TTkCheckbox(size=(10,1), text="", checked=bool(user_data.is_trusted)),  # , alignment=ttk.TTkK.CENTER_ALIGN),
            ttk.TTkCheckbox(size=(10,1), text="", checked=bool(user_data.notify_status)),  # , alignment=ttk.TTkK.CENTER_ALIGN),
            ttk.TTkCheckbox(size=(10,1), text="", checked=bool(user_data.is_prioritized)),  # , alignment=ttk.TTkK.CENTER_ALIGN),
            str(h_last_seen),
            str(user_data.note),
        ], select_row=select_row)

        buddy_item.setIcon(0, USER_STATUS_ICONS.get(status))

        self.addTopLevelItem(buddy_item)

        #for combobox in (
        #    self.window.search.user_search_combobox,
        #    self.window.userbrowse.userbrowse_combobox,
        #    self.window.userinfo.userinfo_combobox
        #):
        #    combobox.append(str(user))

        #self.update_visible()

    def on_remove_buddy(self, *_args):
        core.buddies.remove_buddy(self.get_selected_username())

    def remove_buddy(self, user):

        buddy_item = self.buddy_items.get(user)

        if buddy_item is None:
            return

        buddy_index = self.indexOfTopLevelItem(buddy_item)
        self.takeTopLevelItem(buddy_index)
        del self.buddy_items[user]

        #self.update()

        #for combobox in (
        #    self.window.search.user_search_combobox,
        #    self.window.userbrowse.userbrowse_combobox,
        #    self.window.userinfo.userinfo_combobox
        #):
        #    combobox.remove_id(user)

    def buddy_trusted(self, user, is_trusted):

        buddy_item = self.buddy_items.get(user)

        if buddy_item is not None and buddy_item.widget(5).isChecked() != is_trusted:
            buddy_item.widget(5).setChecked(is_trusted)

    def buddy_notify(self, user, notify_status):

        buddy_item = self.buddy_items.get(user)

        if buddy_item is not None and buddy_item.widget(6).isChecked() != notify_status:
            buddy_item.widget(6).setChecked(notify_status)

    def buddy_prioritized(self, user, is_prioritized):

        buddy_item = self.buddy_items.get(user)

        if buddy_item is not None and buddy_item.widget(7).isChecked() != is_prioritized:
            buddy_item.widget(7).setChecked(is_prioritized)

    def buddy_last_seen(self, user, online):

        buddy_item = self.buddy_items.get(user)

        if buddy_item is None:
            return

        last_seen = UINT64_LIMIT
        h_last_seen = ""

        if not online:
            last_seen = time.time()
            h_last_seen = time.strftime("%x %X", time.localtime(last_seen))

        buddy_item.setData(8, h_last_seen)

    def user_country(self, user, country_code):

        buddy_item = self.buddy_items.get(user)

        if buddy_item is None:
            return

        buddy_item.setData(2, country_code)

    def user_status(self, msg):

        buddy_item = self.buddy_items.get(msg.user)

        if buddy_item is None:
            return

        status = msg.status

        buddy_item.setData(0, USER_STATUS_LABELS.get(status))
        buddy_item.setIcon(0, USER_STATUS_ICONS.get(status))

    def user_stats(self, msg):

        buddy_item = self.buddy_items.get(msg.user)

        if buddy_item is None:
            return

        speed = msg.avgspeed or 0
        num_files = msg.files or 0

        h_speed = human_speed(speed) if speed > 0 else ""
        h_files = humanize(num_files)

        buddy_item.setData(3, h_speed, emit=False)
        buddy_item.setData(4, h_files)

    def on_add_note(self, *_args):
        pass  ##

    def server_disconnect(self, *_args):
        for buddy_item in self.buddy_items.values():
            buddy_item.setData(0, USER_STATUS_LABELS[UserStatus.OFFLINE])
            buddy_item.setIcon(0, USER_STATUS_ICONS[UserStatus.OFFLINE])

    def get_selected_username(self):

        for user_item in self.selectedItems():
            return user_item.username  # data(1).toAscii()  # _text

        return None

    def mouseEvent(self, evt):

        ret = super().mouseEvent(evt)

        if evt.evt == ttk.TTkK.Press:
            if self.popup_menu is not None:
                self.popup_menu._note.menuButtonClicked.clear()
                self.popup_menu._note.close()
                self.popup_menu._remove.menuButtonClicked.clear()
                self.popup_menu._remove.close()
                self.popup_menu.close()

            if evt.key == ttk.TTkK.RightButton:
                username = self.get_selected_username()
                buddy_item = self.buddy_items.get(username)

                if username is None or buddy_item is None:
                    return

                self.popup_menu = UserPopupMenu(self, username, "userlist")

                self.popup_menu._note = self.popup_menu.addMenu("  " + _("Add User _Note…"))
                self.popup_menu._note.menuButtonClicked.connect(self.on_add_note)
                self.popup_menu.addSpacer()
                self.popup_menu._remove = self.popup_menu.addMenu("  " + _("Remove"))
                self.popup_menu._remove.menuButtonClicked.connect(self.on_remove_buddy)

                self.popup_menu.popup(evt.x, evt.y)
                return True

        return ret


class Buddy(ttk.TTkTreeWidgetItem):

    def __init__(self, data, select_row=False, **kwargs):
        super().__init__(data, **kwargs)

        self.username = data[1]

        data[5].toggled.connect(self.on_trusted)
        data[6].toggled.connect(self.on_notify)
        data[7].toggled.connect(self.on_prioritized)

        if select_row:
            self.setSelected(True)

    @ttk.pyTTkSlot(bool)
    def on_trusted(self, is_trusted):
        core.buddies.set_buddy_trusted(self.username, is_trusted)

    @ttk.pyTTkSlot(bool)
    def on_notify(self, notify_status):
        core.buddies.set_buddy_notify(self.username, notify_status)

    @ttk.pyTTkSlot(bool)
    def on_prioritized(self, is_prioritized):
        core.buddies.set_buddy_prioritized(self.username, is_prioritized)

    def setData(self, column, value, emit=True):

        self.data(column)._text, self.data(column)._colors = ttk.TTkString._parseAnsi(str(value))

        if emit:
            self.emitDataChanged()
