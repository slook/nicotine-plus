# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.utils import humanize


PRIVATE_USERS_OFFSET = 10000000


class RoomList(ttk.TTkList):

    def __init__(self, application):
        super().__init__(showSearch=False, name="roomlist")

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
        self.on_close(self.room_list_window)
        self.clear()
        self.close()
        # super().destroy()

    def present(self):

        if self.room_list_window is not None:
            self.on_close(self.room_list_window)
            self.screen.on_focus()
            return

        self.room_list_window = ttk.TTkWindow(
            title=_("All Rooms"),
            size=(min(50, self.screen.width()), int(0.85 * self.screen.height()))
        )
        self.room_list_window.closed.connect(self.on_close)
        self.room_list_window.setLayout(ttk.TTkVBoxLayout())

        top_bar = ttk.TTkContainer(parent=self.room_list_window, layout=ttk.TTkHBoxLayout(), maxHeight=1)
        top_bar.addWidget(ttk.TTkSpacer(minWidth=1, maxWidth=1))
        top_bar.addWidget(self.search_entry)
        top_bar.addWidget(self.search_clear)
        top_bar.addWidget(self.refresh_button)

        self.list_container = ttk.TTkFrame(parent=self.room_list_window, layout=ttk.TTkVBoxLayout())
        self.list_container.addWidget(self)

        foot_bar = ttk.TTkContainer(parent=self.room_list_window, layout=ttk.TTkVBoxLayout(), maxHeight=2)
        foot_bar.addWidget(self.public_feed_toggle)
        foot_bar.addWidget(self.private_room_toggle)

        x = (self.screen.width() // 2) - (self.room_list_window.width() // 2)
        y = (self.screen.height() // 2) - (self.room_list_window.height() // 2)

        ttk.TTkHelper.overlay(self.screen, self.room_list_window, x, y)

    def add_room(self, room, user_count=0, is_private=False, is_owned=False):

        self.room_items[room] = room_item = RoomItem(self, room, user_count, is_private, is_owned)

        index = 0
        for i, listed_room in enumerate(self.items()):
            index = i
            if user_count > listed_room.user_count:
                break

        #room_item.setParent(self.list_container)
        self.addItemAt(room_item, index)

        if self.list_container is not None and not self.list_container.isVisible():
            self.list_container.setVisible(True)

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

        elif user_count == room_item.user_count:
            return

        is_selected = room_item in self.selectedItems()

        self.removeItem(room_item)
        self.add_room(room, user_count=user_count, is_private=room_item.is_private, is_owned=room_item.is_owned)

        if is_selected:
            self.setCurrentItem(self.room_items.get(room))

    def clear(self, *_args):
        self.on_search_clear()
        while self.items():
            self.removeAt(0)
        self.room_items.clear()

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

        #self.freeze()
        self.clear()

        for room, user_count in msg.ownedprivaterooms:
            self.add_room(room, user_count, is_private=True, is_owned=True)

        for room, user_count in msg.otherprivaterooms:
            self.add_room(room, user_count, is_private=True)

        for room, user_count in msg.rooms:
            self.add_room(room, user_count)

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
        self.setSearch(text.toAscii())

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
            self.list_container.removeWidget(self)
            self.room_list_window.closed.clear()
            self.room_list_window.close()
            self.room_list_window = None

        self.on_search_clear()


class RoomItem(ttk.TTkAbstractListItem):

    def __init__(self, room_list, name, user_count, is_private, is_owned):

        style = ttk.TTkColor.RST
        h_user_count = humanize(user_count)

        if is_private:
            style += ttk.TTkColor.BOLD
            user_count += PRIVATE_USERS_OFFSET

        if is_owned:
            style += ttk.TTkColor.UNDERLINE

        text = f"{name:<30} {h_user_count:>5}"
        string = ttk.TTkString(text, style)

        self.room_list = room_list
        self.user_count = user_count
        self.is_private = is_private
        self.is_owned = is_owned

        super().__init__(text=string, data=name)

    def mousePressEvent(self, evt):

        if evt.key == ttk.TTkK.RightButton:
            room = self.data()

            is_private_room_owned = core.chatrooms.is_private_room_owned(room)
            is_private_room_member = core.chatrooms.is_private_room_member(room)

            popup_menu = ttk.TTkMenu(parent=self.room_list, title=room)

            popup_menu._join = popup_menu.addMenu(_("_Join Room"))
            popup_menu._join.setEnabled(room not in core.chatrooms.joined_rooms)
            popup_menu._join.menuButtonClicked.connect(self.on_popup_join)

            popup_menu._leave = popup_menu.addMenu(_("_Leave Room"))
            popup_menu._leave.setEnabled(room in core.chatrooms.joined_rooms)
            popup_menu._leave.menuButtonClicked.connect(self.on_popup_leave)

            popup_menu._spacer = popup_menu.addSpacer()

            popup_menu._disown = popup_menu.addMenu(_("Disown Private Room"))
            popup_menu._disown.setEnabled(is_private_room_owned)
            popup_menu._disown.menuButtonClicked.connect(self.on_popup_private_room_disown)

            popup_menu._cancel = popup_menu.addMenu(_("Cancel Room Membership"))
            popup_menu._cancel.setEnabled(is_private_room_member and not is_private_room_owned)
            popup_menu._cancel.menuButtonClicked.connect(self.on_popup_private_room_cancel_membership)

            ttk.TTkHelper.overlay(self, popup_menu, evt.x, evt.y)

        return super().mousePressEvent(evt)

    def mouseDoubleClickEvent(self, evt):
        self.on_popup_join()
        return True

    def on_popup_join(self, *_args):
        core.chatrooms.show_room(self.data())
        self.room_list.room_list_window.close()

    def on_popup_leave(self, *_args):
        core.chatrooms.remove_room(self.data())

    def on_popup_private_room_disown(self, *_args):
        core.chatrooms.request_private_room_disown(self.data())

    def on_popup_private_room_cancel_membership(self, *_args):
        core.chatrooms.request_private_room_cancel_membership(self.data())
