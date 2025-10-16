# SPDX-FileCopyrightText: 2022-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import time

from collections import deque

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS
from pynicotine.utils import encode_path


class ChatHistory(ttk.TTkTree):

    def __init__(self, application):
        super().__init__(name="chathistory")

        self.screen = application.screen
        self.chat_history_window = None
        self.list_container = None

        self.search_entry = ttk.TTkLineEdit(hint=_("Search users…"))
        self.search_entry.textChanged.connect(self.on_search)
        self.search_entry.returnPressed.connect(self.on_enter)
        self.search_clear = ttk.TTkButton(
            text=ttk.TTkString("<", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
        )
        self.search_clear.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.search_clear.clicked.connect(self.on_search_clear)

        self.history_items = {}

        self.itemActivated.connect(self.on_show_user)
        self.setHeaderLabels([
            " ",
            _("User"),
            _("Latest Message"),
        ])

        for col, width in enumerate([3, 30, 75]):
            self.setColumnWidth(col, width)

        self.load_users()

        for event_name, callback in (
            ("server-login", self.server_login),
            ("server-disconnect", self.server_disconnect),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def destroy(self):
        self.on_close(self.chat_history_window)
        self.clear()
        self.close()
        # super().destroy()

    def present(self):

        if self.chat_history_window is not None:
            self.on_close(self.chat_history_window)
            self.screen.on_focus()
            return

        self.chat_history_window = ttk.TTkWindow(
            title=_("Chat History"),
            size=(min(120, self.screen.width()), int(0.75 * self.screen.height()))
        )
        self.chat_history_window.closed.connect(self.on_close)
        self.chat_history_window.setLayout(ttk.TTkVBoxLayout())

        top_bar = ttk.TTkContainer(parent=self.chat_history_window, layout=ttk.TTkHBoxLayout(), maxHeight=1)
        top_bar.addWidget(ttk.TTkSpacer(minWidth=1, maxWidth=1))
        top_bar.addWidget(self.search_entry)
        top_bar.addWidget(self.search_clear)

        self.list_container = ttk.TTkFrame(parent=self.chat_history_window, layout=ttk.TTkVBoxLayout())
        self.list_container.addWidget(self)

        x = (self.screen.width() // 2) - (self.chat_history_window.width() // 2)
        y = (self.screen.height() // 2) - (self.chat_history_window.height() // 2)

        ttk.TTkHelper.overlay(self.screen, self.chat_history_window, x, y)

    def server_login(self, msg):

        if not msg.success:
            return

        # for history_item in self.history_items
        for history_item in self.invisibleRootItem().children():
            username = history_item.data(1).toAscii()  # _text
            core.users.watch_user(username, context="chathistory")

    def server_disconnect(self, *_args):
        for history_item in self.invisibleRootItem().children():
            history_item.setData(0, USER_STATUS_LABELS[UserStatus.OFFLINE])
            history_item.setIcon(0, USER_STATUS_ICONS[UserStatus.OFFLINE])

    @staticmethod
    def load_user(file_path):
        """Reads the username and latest message from a given log file path.

        Usernames are first extracted from the file name. In case the
        extracted username contains underscores, attempt to fetch the
        original username from logged messages, since illegal filename
        characters are substituted with underscores.
        """

        username = os.path.basename(file_path[:-4]).decode("utf-8", "replace")
        is_safe_username = ("_" not in username)
        login_username = config.sections["server"]["login"]
        timestamp = os.path.getmtime(file_path)

        read_num_lines = 1 if is_safe_username else 25
        latest_message = None

        with open(file_path, "rb") as lines:
            lines = deque(lines, read_num_lines)

            for line in lines:
                try:
                    line = line.decode("utf-8")

                except UnicodeDecodeError:
                    line = line.decode("latin-1")

                if latest_message is None:
                    latest_message = line

                    if is_safe_username:
                        break

                    username_chars = set(username.replace("_", ""))

                if login_username in line:
                    continue

                if " [" not in line or "] " not in line:
                    continue

                start = line.find(" [") + 2
                end = line.find("] ", start)
                line_username_len = (end - start)

                if len(username) != line_username_len:
                    continue

                line_username = line[start:end]

                if username == line_username:
                    # Nothing to do, username is already correct
                    break

                if username_chars.issubset(line_username):
                    username = line_username
                    break

        return username, latest_message, timestamp

    def load_users(self):

        self._treeView.setSortingEnabled(False)
        #self.sortItems(-1, ttk.TTkK.AscendingOrder)

        try:
            with os.scandir(encode_path(log.private_chat_folder_path)) as entries:
                for entry in entries:
                    if not entry.is_file() or not entry.name.endswith(b".log"):
                        continue

                    try:
                        username, latest_message, timestamp = self.load_user(entry.path)

                    except OSError:
                        continue

                    if latest_message is not None:
                        self.update_user(username, latest_message.strip(), timestamp)

        except OSError:
            pass

        self._treeView.setSortingEnabled(True)
        self.sortItems(2, ttk.TTkK.DescendingOrder)  # Latest Message

    def remove_user(self, username, unwatch_user=True):

        for history_item in self.invisibleRootItem().children():
            if history_item.data(1).toAscii() != username:
                continue

            history_index = self.users_list.indexOfTopLevelItem(history_item)
            _old_history_item = self.users_list.takeTopLevelItem(history_index)
            break

        if username in self.history_items:
            del self.history_items[username]

        if unwatch_user:
            core.users.unwatch_user(username, context="chathistory")

    def update_user(self, username, message, timestamp=None):

        self.remove_user(username, unwatch_user=False)
        core.users.watch_user(username, context="chathistory")

        if not timestamp:
            timestamp_format = config.sections["logging"]["log_timestamp"]
            timestamp = time.time()
            h_timestamp = time.strftime(timestamp_format)
            message = f"{h_timestamp} [{username}] {message}"

        status = core.users.statuses.get(username, UserStatus.OFFLINE)

        self.history_items[username] = history_item = HistoryItem([
            USER_STATUS_LABELS[status],
            username,
            message,
            int(timestamp)
        ], select_row=False)

        history_item.setIcon(0, USER_STATUS_ICONS.get(status))

        self.addTopLevelItem(history_item)

    def user_status(self, msg):

        history_item = self.history_items.get(msg.user)

        if history_item is None:
            return

        status_label = USER_STATUS_LABELS.get(msg.status)

        if status_label and status_label != history_item.data(0).toAscii():
            history_item.setData(0, status_label)
            history_item.setIcon(0, USER_STATUS_ICONS.get(msg.status))

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_show_user(self, history_item, _col):
        username = history_item.data(1).toAscii()
        core.privatechat.show_user(username)
        self.on_close(self.chat_history_window)

    @ttk.pyTTkSlot(str)
    def on_search(self, text):

        text = text.toAscii()  # ._text

        for history_item in self.invisibleRootItem().children():
            history_item.setHidden(not any([history_item.data(1).find(text)>-1, history_item.data(2).find(text)>-1]))

    @ttk.pyTTkSlot()
    def on_search_clear(self):
        self.search_entry.setText(ttk.TTkString(""))
        if self.chat_history_window is not None:
            self.search_entry.setFocus()

    @ttk.pyTTkSlot()
    def on_enter(self):
        for history_item in self.selectedItems():
            self.on_show_user(history_item, 1)
            break

    @ttk.pyTTkSlot(ttk.TTkWidget)
    def on_close(self, window):

        if window is not None:
            self.list_container.removeWidget(self)
            self.chat_history_window.closed.clear()
            self.chat_history_window.close()
            self.chat_history_window = None

        self.on_search_clear()


class HistoryItem(ttk.TTkTreeWidgetItem):

    def __init__(self, data, select_row=False, timestamp=None):
        super().__init__(data)

        #self.username = data[1]
        self.timestamp = timestamp

        if select_row:
            self.setSelected(True)

    def setData(self, column, value, emit=True):

        self.data(column)._text, self.data(column)._colors = ttk.TTkString._parseAnsi(str(value))

        if emit:
            self.emitDataChanged()
