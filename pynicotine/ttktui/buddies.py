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
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS
from pynicotine.ttktui.widgets.trees import UsersList
from pynicotine.utils import UINT64_LIMIT
# from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class BuddyItem(ttk.TTkTreeWidgetItem):

    def __init__(self, data, **kwargs):
        super().__init__(data, **kwargs)

        # Store the raw values
        self.status = data[0]
        self.username = data[1]
        self.num_files = data[2]
        self.num_folders = data[3]
        self.upload_speed = data[4] or 0
        self.last_seen = data[9]

        # Transform the raw values into formatted strings
        data[0] = USER_STATUS_LABELS.get(self.status, "")

        data[2] = f"{self.num_files:8d}" if self.num_files is not None else ""  # humanize(self.files)
        data[3] = f"{self.num_folders:8d}" if self.num_folders is not None else ""
        data[4] = f"{human_speed(self.upload_speed):>12}" if self.upload_speed > 0 else ""

        data[6] = ttk.TTkCheckbox(size=(3, 1), text="", checked=bool(data[6]))  # , alignment=ttk.TTkK.CENTER_ALIGN),
        data[7] = ttk.TTkCheckbox(size=(3, 1), text="", checked=bool(data[7]))  # , alignment=ttk.TTkK.CENTER_ALIGN),
        data[8] = ttk.TTkCheckbox(size=(3, 1), text="", checked=bool(data[8]))  # , alignment=ttk.TTkK.CENTER_ALIGN),

        data[9] = self.get_last_seen()

        super().__init__(data, icon=USER_STATUS_ICONS.get(self.status), **kwargs)

        self.widget(6).toggled.connect(self.on_trusted)
        self.widget(7).toggled.connect(self.on_notify)
        self.widget(8).toggled.connect(self.on_prioritized)

        self.username_data = self.username.lower()

    @ttk.pyTTkSlot(bool)
    def on_trusted(self, is_trusted):
        core.buddies.set_buddy_trusted(self.username, is_trusted)

    @ttk.pyTTkSlot(bool)
    def on_notify(self, notify_status):
        core.buddies.set_buddy_notify(self.username, notify_status)

    @ttk.pyTTkSlot(bool)
    def on_prioritized(self, is_prioritized):
        core.buddies.set_buddy_prioritized(self.username, is_prioritized)

    def get_last_seen(self):

        if self.last_seen:
            try:
                last_seen_time = time.strptime(self.last_seen, "%m/%d/%Y %H:%M:%S")
                self.last_seen = time.mktime(last_seen_time)
                return time.strftime("%x %X", last_seen_time)

            except ValueError:
                self.last_seen = 0
                return _("Never seen")

        return ""

    def name(self):
        return self.username

    def setData(self, column, value, emit=True):

        if column == 0:
            if value is None or value == self.status:
                return
            self.status = value
            value = USER_STATUS_LABELS.get(self.status, "")

        elif column == 2:
            if value == self.num_files:
                return
            self.num_files = value
            value = f"{self.num_files:8d}" if self.num_files is not None else ""  # humanize(self.num_files)

        if column == 3:
            if value == self.num_folders:
                return
            self.num_folders = value
            value = f"{self.num_folders:8d}" if self.num_folders is not None else ""

        elif column == 4:
            if value is None or value == self.upload_speed:
                return
            self.upload_speed = value or 0
            value = f"{human_speed(self.upload_speed):>12}" if self.upload_speed > 0 else ""

        elif column == 5:
            pass  # country

        elif column in {6, 7, 8}:
            pass  # self.widget(column).setChecked(value)

        elif column == 9:
            if value is None or value == self.last_seen:
                return
            self.last_seen = value
            value = time.strftime("%x %X", time.localtime(self.last_seen)) if self.last_seen < UINT64_LIMIT else ""

        elif column == 10:
            pass  # note

        # Hack the new value into the existing string object of the model
        self.data(column)._text, self.data(column)._colors = ttk.TTkString._parseAnsi(str(value))

        if column == 0:
            self.setIcon(0, USER_STATUS_ICONS.get(self.status))

        elif emit:
            self.emitDataChanged()

    def sortData(self, col):

        if col == 1:
            return self.username_data

        if col == 2:
            return self.num_files or 0

        if col == 3:
            return self.num_folders or 0

        if col == 4:
            return self.upload_speed or 0

        if col == 5:
            pass  # country

        if col in {6, 7, 8}:
            return self.widget(col).isChecked()

        if col == 9:
            return self.last_seen

        if col == 10:
            pass  # note

        return str(self.data(col))


class BuddiesList(UsersList):

    class UserItem(BuddyItem):
        pass

    def __init__(self, parent=None, **kwargs):
        super().__init__(
            parent=parent,
            header=[
                " ",         # 0
                _("User"),   # 1 * _KEY_COLUMN
                _("Files"),  # 2
                _("Folders"),  # 3
                _("Speed"),    # 4
                _("Country"),  # 5
                _("Trusted"),      # 6
                _("Notify"),       # 7
                _("Prioritized"),  # 8
                _("Last Seen"),    # 9
                _("Note"),         # 10
                # "11",
                # "12"
            ],
            **kwargs
        )

        # Columns                    0  *1  2  3   4  5  6  7   8   9  10
        for col, width in enumerate([3, 30, 8, 8, 12, 8, 8, 8, 12, 20, 40]):
            self.setColumnWidth(col, width)

    def clear(self):
        for buddy_item in self.iterators.values():
            for checkbox in (buddy_item.widget(6), buddy_item.widget(7), buddy_item.widget(8)):
                checkbox.toggled.clear()
                checkbox.close()
        super().clear()

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_user_item_activated(self, buddy_item, col):

        if col == 10:
            self.parentWidget().on_add_note()
            return

        core.userinfo.show_user(str(buddy_item.name()))  # data(self._KEY_COLUMN)))


class Buddies(ttk.TTkContainer):

    def __init__(self, screen, name="userlist"):
        super().__init__(layout=ttk.TTkVBoxLayout(), name=name)

        self.screen = screen

        self.header_bar = None
        self.buddies_list = None

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout())
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[name]
        )
        self._placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN,
            text=_("Add users as buddies to share specific folders with them "
                   "and receive notifications when they are online").replace(" and ", "\nand ")
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        # Events
        for event_name, callback in (
            ("add-buddy", self.add_buddy_row),
            ("buddy-note", self.buddy_note),
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

    def create_header(self):

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        self.header_bar.layout().addWidget(ttk.TTkSpacer())

        self.entry_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString("+", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5
        )
        self.entry_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.entry_button.clicked.connect(self.on_entry_clicked)

        self.add_buddy_entry = ttk.TTkLineEdit(
            parent=self.header_bar,
            hint=_("Add buddy…")
        )
        self.add_buddy_entry.setMinimumWidth(core.users.USERNAME_MAX_LENGTH)
        self.add_buddy_entry.setMaximumWidth(core.users.USERNAME_MAX_LENGTH)
        self.add_buddy_entry.returnPressed.connect(self.on_entry_pressed)

        self.header_bar.layout().addWidget(ttk.TTkSpacer())

        for widget in (self.entry_button, self.add_buddy_entry):
            widget.setToolTip(self._placeholder.text())

    def destroy(self):
        self.entry_button.clicked.disconnect(self.on_entry_clicked)
        self.add_buddy_entry.returnPressed.disconnect(self.on_entry_pressed)
        self.add_buddy_entry.close()
        self.buddies_list.clear()
        self.buddies_list.close()
        # self.close()

    def start(self):

        self.buddies_list = BuddiesList(parent=self, visible=False)

        self.add_buddy_rows(core.buddies.users)
        self.buddies_list.sortItems(1, ttk.TTkK.AscendingOrder)  # User

    def focus_default_widget(self):

        if self.screen.tab_bar.currentWidget() != self:
            return

        self.add_buddy_entry.setFocus()

    def on_tab_switched(self):
        self.screen.focus_default_widget()

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def set_buddy_list_position(self, button):

        if button.isChecked():
            config.sections["ui"]["modes_visible"]["userlist"] = False
            config.sections["ui"]["buddylistinchatrooms"] = "always"

            self.screen.hide_tab("userlist")
            self.screen.side_bar.setVisible(True)

            # self.screen.setWidget(widget=self, position=self.screen.RIGHT, size=35)

        else:
            config.sections["ui"]["modes_visible"]["userlist"] = True
            config.sections["ui"]["buddylistinchatrooms"] = "tab"
            self.screen.side_bar.setVisible(False)

            # self.screen.layout().removeWidget(widget=self)  # , position=self.screen.RIGHT)

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

    def add_buddy_row(self, user, user_data, select_row=True):

        buddy_item = self.buddies_list.add_row(self._generate_buddy_row(user_data))

        if not self.buddies_list.isVisible():
            self.buddies_list.setVisible(True)
            self._spacer.setVisible(False)

        if select_row:
            self.buddies_list.selectItem(buddy_item)

        for combobox in (
            self.screen.search.user_search_combobox,
            self.screen.userbrowse.userbrowse_combobox,
            self.screen.userinfo.userinfo_combobox
        ):
            combobox.addItem(user)

    def add_buddy_rows(self, buddies):

        self.buddies_list.add_rows(self._generate_buddy_row(buddy) for buddy in buddies.values())

        if buddies and not self.buddies_list.isVisible():
            self.buddies_list.setVisible(True)
            self._spacer.setVisible(False)

        for combobox in (
            self.screen.search.user_search_combobox,
            self.screen.userbrowse.userbrowse_combobox,
            self.screen.userinfo.userinfo_combobox
        ):
            combobox.addItems(sorted(list(buddies.keys())))

    @staticmethod
    def _generate_buddy_row(buddy):

        username = buddy.username
        status = buddy.status
        country_code = core.users.countries.get(username)
        stats = core.users.watched.get(username)

        if stats is not None:
            num_files = stats.num_files
            num_folders = stats.num_folders
            upload_speed = stats.upload_speed or 0
            country_code = country_code or stats.country
        else:
            num_files = None
            num_folders = None
            upload_speed = 0

        if country_code:
            country_code = country_code.replace("flag_", "")

        return [
            status,
            username,
            num_files,
            num_folders,
            upload_speed,
            country_code,  # get_flag_icon_name(country_code),
            buddy.is_trusted,
            buddy.notify_status,
            buddy.is_prioritized,
            buddy.last_seen,
            buddy.note,
        ]

    def on_remove_buddy(self, *_args):

        for buddy_item in self.buddies_list.selectedItems():
            username = buddy_item.username  # str(buddy_item.data(self.buddies_list._KEY_COLUMN))
            core.buddies.remove_buddy(username)
            break

    def remove_buddy(self, username):

        buddy_item = self.buddies_list.iterators.get(username)

        if buddy_item is None:
            return

        buddy_index = self.buddies_list.indexOfTopLevelItem(buddy_item)
        self.buddies_list.takeTopLevelItem(buddy_index)
        del self.buddies_list.iterators[username]

        if not self.buddies_list.iterators:
            self.buddies_list.setVisible(False)
            self._spacer.setVisible(True)

        for combobox in (
            self.screen.search.user_search_combobox,
            self.screen.userbrowse.userbrowse_combobox,
            self.screen.userinfo.userinfo_combobox
        ):
            combobox._list.remove(username)

    def buddy_trusted(self, username, is_trusted):

        buddy_item = self.buddies_list.iterators.get(username)

        if buddy_item is not None and buddy_item.widget(6).isChecked() != is_trusted:
            buddy_item.widget(6).setChecked(is_trusted)

    def buddy_notify(self, username, notify_status):

        buddy_item = self.buddies_list.iterators.get(username)

        if buddy_item is not None and buddy_item.widget(7).isChecked() != notify_status:
            buddy_item.widget(7).setChecked(notify_status)

    def buddy_prioritized(self, username, is_prioritized):

        buddy_item = self.buddies_list.iterators.get(username)

        if buddy_item is not None and buddy_item.widget(8).isChecked() != is_prioritized:
            buddy_item.widget(8).setChecked(is_prioritized)

    def buddy_last_seen(self, username, online):

        buddy_item = self.buddies_list.iterators.get(username)

        if buddy_item is None:
            return

        buddy_item.setData(9, UINT64_LIMIT if online else time.time())

    def user_country(self, username, country_code):

        buddy_item = self.buddies_list.iterators.get(username)

        if buddy_item is None:
            return

        buddy_item.setData(5, country_code)

    def user_status(self, msg):

        buddy_item = self.buddies_list.iterators.get(msg.username)

        if buddy_item is None:
            return

        buddy_item.setData(0, msg.status)

    def user_stats(self, msg):

        buddy_item = self.buddies_list.iterators.get(msg.username)

        if buddy_item is None:
            return

        stats = msg.stats
        buddy_item.setData(4, stats.upload_speed)
        buddy_item.setData(3, stats.num_folders)
        buddy_item.setData(2, stats.num_files)

    def buddy_note(self, username, note):

        buddy_item = self.buddies_list.iterators.get(username)

        if buddy_item is None:
            return

        buddy_item.setData(10, note)

    def on_add_note(self, *_args):

        buddy_item = username = old_note = None

        for buddy_item in self.buddies_list.selectedItems():
            username = buddy_item.username
            old_note = str(buddy_item.data(10))
            break

        if buddy_item is None:
            return

        from pynicotine.ttktui.widgets.dialogs import EntryDialog

        def response(dialog, _response_id, username):

            new_note = dialog.get_entry_value()

            if new_note == old_note:
                return

            core.buddies.set_buddy_note(username, new_note)

        EntryDialog(
            parent=self.screen,
            title=_("Add User Note"),
            message=_("Add a note about user %s:") % username,
            default=old_note,
            action_button_label=_("_Add"),
            callback=response,
            callback_data=username
        ).present()
        return

    def server_disconnect(self, *_args):
        for buddy_item in self.buddies_list.iterators.values():
            buddy_item.setData(0, UserStatus.OFFLINE)
