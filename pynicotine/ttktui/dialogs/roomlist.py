# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.utils import humanize


class RoomList(ttk.TTkTree):

    def __init__(self, application):
        super().__init__(header=[_("Room"), _("Users")], name="roomlist")

        self.screen = application.screen
        self.room_list_window = None
        self.list_container = None

        self.search_entry = ttk.TTkLineEdit(hint=_("Search rooms…"))
        self.search_entry.textChanged.connect(self.on_search)
        self.search_entry.returnPressed.connect(self.on_enter)
        self.search_clear = ttk.TTkButton(
            text=ttk.TTkString("<", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
        )
        self.search_clear.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.search_clear.clicked.connect(self.on_search_clear)

        self.refresh_button = ttk.TTkButton(text=_("Refresh Rooms"), maxWidth=17)
        self.refresh_button.clicked.connect(self.on_refresh)

        self.public_feed_toggle = ttk.TTkCheckbox(text=_("_Show feed of public chat room messages"), checked=False)
        self.public_feed_toggle.toggled.connect(self.on_toggle_public_feed)

        self.private_room_toggle = ttk.TTkCheckbox(text=_("_Accept private room invitations"), checked=False)
        self.private_room_toggle.setChecked(config.sections["server"]["private_chatrooms"])
        self.private_room_toggle.toggled.connect(self.on_toggle_accept_private_room)

        self.room_items = {}
        self.setColumnWidth(0, 30)
        self.setColumnWidth(1, 10)

        self.popup_room = None
        self.popup_menu = None

        self.itemActivated.connect(self.on_activated)

        for event_name, callback in (
            ("join-room", self.join_room),
            ("private-room-added", self.private_room_added),
            ("remove-room", self.remove_room),
            ("room-list", self.room_list),
            ("server-disconnect", self.clear),
            ("show-room", self.show_room),
            ("user-joined-room", self.user_joined_room),
            ("user-left-room", self.user_left_room)
        ):
            events.connect(event_name, callback)

    def destroy(self):
        self.public_feed_toggle.toggled.disconnect(self.on_toggle_public_feed)
        self.private_room_toggle.toggled.disconnect(self.on_toggle_accept_private_room)
        self.refresh_button.clicked.disconnect(self.on_refresh)
        self.search_clear.clicked.disconnect(self.on_search_clear)
        self.search_entry.textChanged.disconnect(self.on_search)
        self.search_entry.returnPressed.disconnect(self.on_enter)
        self.search_entry.clearFocus()
        self.search_entry.close()

        self.on_close(self.room_list_window)
        self.clear()
        self.close()
        # super().destroy()

    def present(self):

        if self.room_list_window is not None:
            self.on_close(self.room_list_window)
            return

        self.room_list_window = ttk.TTkWindow(
            title=_("All Rooms"),
            size=(min(50, self.screen.width()), int(0.85 * self.screen.height()))
        )
        self.room_list_window.closed.connect(self.on_close)
        self.room_list_window.setLayout(ttk.TTkVBoxLayout())

        top_bar = ttk.TTkContainer(parent=self.room_list_window, layout=ttk.TTkHBoxLayout(), maxHeight=1)
        top_bar.layout().addWidget(ttk.TTkSpacer(minWidth=1, maxWidth=1))
        top_bar.layout().addWidget(self.search_entry)
        top_bar.layout().addWidget(self.search_clear)
        top_bar.layout().addWidget(self.refresh_button)

        self.list_container = ttk.TTkFrame(parent=self.room_list_window, layout=ttk.TTkGridLayout())
        self.list_container.layout().addWidget(self)

        foot_bar = ttk.TTkContainer(parent=self.room_list_window, layout=ttk.TTkVBoxLayout(), maxHeight=2)
        foot_bar.layout().addWidget(self.public_feed_toggle)
        foot_bar.layout().addWidget(self.private_room_toggle)

        x = (self.screen.width() // 2) - (self.room_list_window.width() // 2)
        y = (self.screen.height() // 2) - (self.room_list_window.height() // 2)

        ttk.TTkHelper.overlay(self.screen, self.room_list_window, x, y)

        self.search_entry.setFocus()

    def create_popup_menu(self, room):

        is_private_room_owned = core.chatrooms.is_private_room_owned(room)
        is_private_room_member = core.chatrooms.is_private_room_member(room)

        self.popup_room = room
        self.popup_menu = ttk.TTkMenu(title=room)  # parent=self.room_list

        self.popup_menu._join = self.popup_menu.addMenu(_("_Join Room"))
        self.popup_menu._join.setData(room)
        self.popup_menu._join.setEnabled(room not in core.chatrooms.joined_rooms)
        self.popup_menu._join.menuButtonClicked.connect(self.on_popup_join)

        self.popup_menu._leave = self.popup_menu.addMenu(_("_Leave Room"))
        self.popup_menu._leave.setData(room)
        self.popup_menu._leave.setEnabled(room in core.chatrooms.joined_rooms)
        self.popup_menu._leave.menuButtonClicked.connect(self.on_popup_leave)

        self.popup_menu._spacer = self.popup_menu.addSpacer()

        self.popup_menu._disown = self.popup_menu.addMenu(_("Disown Private Room"))
        self.popup_menu._disown.setData(room)
        self.popup_menu._disown.setEnabled(is_private_room_owned)
        self.popup_menu._disown.menuButtonClicked.connect(self.on_popup_private_room_disown)

        self.popup_menu._cancel = self.popup_menu.addMenu(_("Cancel Room Membership"))
        self.popup_menu._cancel.setData(room)
        self.popup_menu._cancel.setEnabled(is_private_room_member and not is_private_room_owned)
        self.popup_menu._cancel.menuButtonClicked.connect(self.on_popup_private_room_cancel_membership)

    def add_room(self, room, user_count=0, is_private=False, is_owned=False):

        self.room_items[room] = room_item = RoomItem(
            [
                room,
                user_count,
            ],
            is_private,
            is_owned
        )
        self.addTopLevelItem(room_item)

        #if self.list_container is not None and not self.list_container.isVisible():
        #    self.list_container.setVisible(True)

    def update_room_user_count(self, room, user_count=None, decrement=False):

        room_item = self.room_items.get(room)

        if room_item is None:
            return

        if user_count is None:
            user_count = room_item.user_count

            if decrement:
                if user_count > 0:
                    user_count -= 1
            else:
                user_count += 1

        room_item.setData(1, user_count)

    def clear(self, *_args):
        self.on_search_clear()
        self.room_items.clear()
        super().clear()

    def private_room_added(self, msg):
        self.add_room(msg.room, is_private=True)

    def join_room(self, msg):

        room = msg.room

        if room not in core.chatrooms.joined_rooms:
            return

        user_count = len(msg.users)

        if room not in self.room_items:
            self.add_room(
                room, user_count, is_private=msg.private,
                is_owned=(msg.owner == core.users.login_username)
            )

        self.update_room_user_count(room, user_count=user_count)

    def show_room(self, room, *_args):
        if room == core.chatrooms.GLOBAL_ROOM_NAME:
            self.public_feed_toggle.setChecked(True)

    def remove_room(self, room):

        if room == core.chatrooms.GLOBAL_ROOM_NAME:
            self.public_feed_toggle.setChecked(False)

        self.update_room_user_count(room, decrement=True)

    def user_joined_room(self, msg):
        if msg.userdata.username != core.users.login_username:
            self.update_room_user_count(msg.room)

    def user_left_room(self, msg):
        if msg.username != core.users.login_username:
            self.update_room_user_count(msg.room, decrement=True)

    def room_list(self, msg):

        # Temporarily disable sorting for increased performance
        self._treeView.setSortingEnabled(False)
        self.clear()

        for room, user_count in msg.ownedprivaterooms:
            self.add_room(room, user_count, is_private=True, is_owned=True)

        for room, user_count in msg.otherprivaterooms:
            self.add_room(room, user_count, is_private=True)

        for room, user_count in msg.rooms:
            self.add_room(room, user_count)

        self._treeView.setSortingEnabled(True)
        self.sortItems(1, ttk.TTkK.DescendingOrder)  # Users
        #self.list_view.unfreeze()

    @ttk.pyTTkSlot(bool)
    def on_toggle_public_feed(self, active):

        global_room_name = core.chatrooms.GLOBAL_ROOM_NAME

        if active:
            if global_room_name not in core.chatrooms.joined_rooms:
                core.chatrooms.show_room(global_room_name)

            self.room_list_window.close()
            return

        core.chatrooms.remove_room(global_room_name)

    @ttk.pyTTkSlot(bool)
    def on_toggle_accept_private_room(self, active):
        config.sections["server"]["private_chatrooms"] = active
        core.chatrooms.request_private_room_toggle(active)

    @ttk.pyTTkSlot()
    def on_refresh(self):
        core.chatrooms.request_room_list()

    @ttk.pyTTkSlot(str)
    def on_search(self, text):
        text = str(text).lower()
        for room_item in self.invisibleRootItem().children():
            room_item.setHidden(text not in room_item.name().lower())

    @ttk.pyTTkSlot()
    def on_search_clear(self):
        self.search_entry.setText(ttk.TTkString(""))
        if self.room_list_window is not None:
            self.search_entry.setFocus()

    @ttk.pyTTkSlot()
    def on_enter(self):
        for room_item in self.selectedItems():
            room_item.on_popup_join()
            break

    @ttk.pyTTkSlot(ttk.TTkWidget)
    def on_close(self, window):

        if window is not None:
            self.list_container.layout().removeWidget(self)
            self.room_list_window.closed.clear()
            self.room_list_window.close()
            self.room_list_window = None

        self.on_search_clear()
        self.screen.focus_default_widget()

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_activated(self, room_item, _column):
        core.chatrooms.show_room(room_item.name())
        self.room_list_window.close()

    def on_popup_join(self, *_args):
        core.chatrooms.show_room(self.popup_room)
        self.room_list_window.close()

    def on_popup_leave(self, *_args):
        core.chatrooms.remove_room(self.popup_room)

    def on_popup_private_room_disown(self, *_args):
        core.chatrooms.request_private_room_disown(self.popup_room)

    def on_popup_private_room_cancel_membership(self, *_args):
        core.chatrooms.request_private_room_cancel_membership(self.popup_room)

    def get_selected_room(self):

        for room_item in self.selectedItems():
            return room_item.name()

        return None

    def mouseEvent(self, evt):

        ret = super().mouseEvent(evt)

        if evt.evt == ttk.TTkK.Press:
            if self.popup_menu is not None:
                self.popup_menu.close()

            self.popup_room = self.get_selected_room()

            if evt.key == ttk.TTkK.RightButton:
                if self.popup_room is None:
                    return False

                self.create_popup_menu(self.popup_room)

                ttk.TTkHelper.overlay(self, self.popup_menu, evt.x, evt.y)

        return ret


class RoomItem(ttk.TTkTreeWidgetItem):

    def __init__(self, data, is_private, is_owned, selected=False, **kwargs):

        self.user_count = data[1]
        self.is_private = is_private

        style = ttk.TTkColor.RST

        if is_private:
            style += ttk.TTkColor.BOLD

        if is_owned:
            style += ttk.TTkColor.UNDERLINE

        self._name = data[0]
        data[0] = ttk.TTkString(data[0], style)
        data[1] = humanize(self.user_count)

        super().__init__(data, selected=selected, **kwargs)

        #self._alignment = [ttk.TTkK.LEFT_ALIGN, ttk.TTkK.LEFT_ALIGN, ttk.TTkK.RIGHT_ALIGN, ttk.TTkK.RIGHT_ALIGN]  #*len(self._data)

        #self.setTextAlignment(3, ttk.TTkK.RIGHT_ALIGN)
        #self.setTextAlignment(4, ttk.TTkK.RIGHT_ALIGN)

    def name(self):
        return self._name

    def setData(self, column, value, emit=True):

        if column == 1:
            if value == self.user_count:
                return

            self.user_count = value
            value = humanize(value)

        self.data(column)._text, self.data(column)._colors = ttk.TTkString._parseAnsi(str(value))

        if emit:
            self.emitDataChanged()

    def sortData(self, col):

        def _privateRoomsTop():
            # Always sort private rooms first regardless of order
            return self.is_private if self._parent._sortOrder == ttk.TTkK.DescendingOrder else (not self.is_private)

        if col == 1:
            # Raw integer sort
            return (_privateRoomsTop(), self.user_count)

        # Alphanumeric split
        parts, c = [], ''
        for char in str(self.data(col)):
            if char.isdigit() == c.isdigit():
                c += char
            else:
                parts.append(c)
                c = char
        parts.append(c)

        return (_privateRoomsTop(), [int(part) if part.isdigit() else part.lower() for part in parts])  # parts
