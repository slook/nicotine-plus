# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
#from pynicotine.utils import humanize
from pynicotine.ttktui.widgets.dialogs import OptionDialog
from pynicotine.ttktui.widgets.menus import PopupMenu


class RoomList(ttk.TTkTree):

    _CLOSED_ICON  = "▫"  # ▱
    _JOINED_ICON  = "▪"  # ▰ 🟁 ◆
    _PRIVATE_ICON = "◇"
    _MEMBER_ICON  = "◈"
    _OWNED_ICON   = "◎"
    _OWNER_ICON   = "◉"

    def __init__(self, application):
        super().__init__(header=[f'   {_("Room")}', f' {_("Users")}'], name="roomlist")

        self.screen = application.screen
        self.window = None
        self.list_container = None
        self.popup_menu = None

        self.search_entry = ttk.TTkLineEdit(hint=_("Search rooms…"), enabled=False)
        self.search_entry.textChanged.connect(self.on_search)
        self.search_entry.returnPressed.connect(self.on_enter)
        self.search_clear = ttk.TTkButton(
            text=ttk.TTkString("<", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}, enabled=False
        )
        self.search_clear.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.search_clear.clicked.connect(self.on_search_clear)

        self.refresh_button = ttk.TTkButton(text=_("Refresh Rooms"), maxWidth=17)
        self.refresh_button.clicked.connect(self.on_refresh)

        self.public_feed_toggle = ttk.TTkCheckbox(text=_("_Show feed of public chat room messages"), checked=False)
        self.room_invitations_toggle = ttk.TTkCheckbox(text=_("_Accept private room invitations"), checked=False)

        self.room_items = {}
        self.setColumnWidth(0, 32)
        self.setColumnWidth(1, 8)

        for event_name, callback in (
            ("join-room", self.join_room),
            ("room-membership-granted", self.room_membership_granted),
            ("room-membership-revoked", self.room_membership_revoked),
            ("remove-room", self.remove_room),
            ("room-list", self.room_list),
            ("server-disconnect", self.clear),
            #("show-room", self.show_room),
            ("user-joined-room", self.user_joined_room),
            ("user-left-room", self.user_left_room)
        ):
            events.connect(event_name, callback)

    def present(self):

        if self.window is not None:
            self.window.close()
            return

        self.window = ttk.TTkWindow(
            layout=ttk.TTkVBoxLayout(),
            title=_("All Rooms") if self.room_items else _("No Chat Rooms"),
            size=(min(49, self.screen.width()), int(0.8 * self.screen.height()))
        )
        self.window.closed.connect(self.on_window_closed)

        top_bar = ttk.TTkContainer(parent=self.window, layout=ttk.TTkHBoxLayout(), maxHeight=1)
        top_bar.layout().addWidget(ttk.TTkSpacer(minWidth=1, maxWidth=1))
        top_bar.layout().addWidget(self.search_entry)
        top_bar.layout().addWidget(self.search_clear)
        top_bar.layout().addWidget(self.refresh_button)

        self.list_container = ttk.TTkFrame(parent=self.window, layout=ttk.TTkGridLayout())
        self.itemActivated.connect(self.on_room_item_activated)
        self._treeView.setSortingEnabled(True)
        self.sortItems(1, ttk.TTkK.DescendingOrder)  # Users
        self.list_container.layout().addWidget(self)

        self.public_feed_toggle.setChecked(core.chatrooms.GLOBAL_ROOM_NAME in core.chatrooms.joined_rooms)
        self.room_invitations_toggle.setChecked(config.sections["server"]["private_chatrooms"])
        self.public_feed_toggle.toggled.connect(self.on_toggle_public_feed)
        self.room_invitations_toggle.toggled.connect(self.on_toggle_room_invitations)

        foot_bar = ttk.TTkContainer(parent=self.window, layout=ttk.TTkVBoxLayout(), paddingLeft=1, maxHeight=2)
        foot_bar.layout().addWidget(self.public_feed_toggle)
        foot_bar.layout().addWidget(self.room_invitations_toggle)

        x = (self.screen.width() // 2) - (self.window.width() // 2)
        y = (self.screen.height() // 2) - (self.window.height() // 2)

        ttk.TTkHelper.overlay(self.screen, self.window, x, y)

        if self.search_entry.isEnabled():
            self.search_entry.setFocus()

    @ttk.pyTTkSlot(ttk.TTkWidget)
    def on_window_closed(self, _window):

        self._treeView.setSortingEnabled(False)
        self.itemActivated.disconnect(self.on_room_item_activated)
        self.public_feed_toggle.toggled.disconnect(self.on_toggle_public_feed)
        self.room_invitations_toggle.toggled.disconnect(self.on_toggle_room_invitations)

        if self.popup_menu is not None:
            self.popup_menu.close()
            self.popup_menu = None

        self.list_container.layout().removeWidget(self)
        self.on_search_clear()
        self.window.closed.clear()
        self.window = None

        self.screen.focus_default_widget()

    def destroy(self):

        self.refresh_button.clicked.disconnect(self.on_refresh)
        self.search_clear.clicked.disconnect(self.on_search_clear)
        self.search_entry.textChanged.disconnect(self.on_search)
        self.search_entry.returnPressed.disconnect(self.on_enter)

        if self.window is not None:
            self.window.close()

        self.clear()
        self.close()

    def clear(self, *args):
        self.on_search_clear()
        self.room_items.clear()
        self.search_entry.setEnabled(False)
        self.search_clear.setEnabled(False)
        self._treeView.setSortingEnabled(False)
        super().clear()

    def get_room_icon_style(self, is_private, is_owner, is_joined):

        icon = self._CLOSED_ICON
        style = ttk.TTkColor.RST

        if is_joined:
            icon = self._JOINED_ICON

        if is_private:
            icon = self._MEMBER_ICON if is_joined else self._PRIVATE_ICON
            style += ttk.TTkColor.BOLD

        if is_owner:
            icon = self._OWNER_ICON if is_joined else self._OWNED_ICON
            style += ttk.TTkColor.UNDERLINE

        return (icon, style)

    def add_room(self, room, user_count=0, is_private=False, is_owner=False, is_joined=None):

        if is_joined is None:
            # Refreshing so have to recheck membership for each room
            is_joined = room in core.chatrooms.joined_rooms

        icon, style = self.get_room_icon_style(is_private, is_owner, is_joined)

        self.room_items[room] = room_item = RoomItem(
            [
                room,
                user_count,
            ],
            is_private,
            style,
            icon=icon
        )
        self.addTopLevelItem(room_item)

        if not self.search_entry.isEnabled():
            if self.window is not None:
                self.window.setTitle(_("All Rooms"))

            self.search_entry.setEnabled(True)
            self.search_clear.setEnabled(True)

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

    def room_membership_granted(self, msg):
        self.add_room(msg.room, is_private=True, is_joined=True)

    def room_membership_revoked(self, msg):

        room_item = self.room_items.get(msg.room)

        if room_item is not None:
            self.takeTopLevelItem(room_item)

    def join_room(self, msg):

        room = msg.room

        if room not in core.chatrooms.joined_rooms:
            return

        user_count = len(msg.users)
        is_private = msg.private
        is_owner = (msg.owner == core.users.login_username)

        if room not in self.room_items:
            self.add_room(
                room,
                user_count,
                is_private=is_private,
                is_owner=is_owner,
                is_joined=True
            )
        elif room_item := self.room_items.get(room):
            icon, _style = self.get_room_icon_style(is_private, is_owner, is_joined=True)
            room_item.setIcon(0, icon)

        self.update_room_user_count(room, user_count=user_count)

    #def show_room(self, room, *_args):
    #    if room == core.chatrooms.GLOBAL_ROOM_NAME:
    #        self.public_feed_toggle.setChecked(True)

    def remove_room(self, room):

        if room == core.chatrooms.GLOBAL_ROOM_NAME:
            #self.public_feed_toggle.setChecked(False)
            pass

        elif room_item := self.room_items.get(room):
            icon, style = self.get_room_icon_style(
                room_item.is_private,
                core.chatrooms.is_room_owner(room),
                is_joined=False
            )
            room_item.setIcon(0, icon)

        self.update_room_user_count(room, decrement=True)

    def user_joined_room(self, msg):
        if msg.userdata.username != core.users.login_username:
            self.update_room_user_count(msg.room)

    def user_left_room(self, msg):
        if msg.username != core.users.login_username:
            self.update_room_user_count(msg.room, decrement=True)

    def room_list(self, msg):

        # Avoid checking membership of each room during startup
        is_refresh = bool(self.invisibleRootItem().children())
        is_joined = None if is_refresh else False

        # Temporarily disable sorting for increased performance
        self.clear()

        for room, user_count in msg.rooms_owner:
            self.add_room(room, user_count, is_private=True, is_owner=True, is_joined=is_joined)

        for room, user_count in msg.rooms_member:
            self.add_room(room, user_count, is_private=True, is_joined=is_joined)

        for room, user_count in msg.rooms:
            self.add_room(room, user_count, is_joined=is_joined)

        self._treeView.setSortingEnabled(True)
        self.sortItems(1, ttk.TTkK.DescendingOrder)  # Users

    @ttk.pyTTkSlot(bool)
    def on_toggle_public_feed(self, active):

        global_room_name = core.chatrooms.GLOBAL_ROOM_NAME

        if active:
            if global_room_name not in core.chatrooms.joined_rooms:
                core.chatrooms.show_room(global_room_name)

            self.window.close()
            return

        core.chatrooms.remove_room(global_room_name)

    @ttk.pyTTkSlot(bool)
    def on_toggle_room_invitations(self, active):
        config.sections["server"]["private_chatrooms"] = active
        core.chatrooms.request_enable_room_invitations(active)

    @ttk.pyTTkSlot()
    def on_refresh(self):
        core.chatrooms.request_room_list()

    @ttk.pyTTkSlot()
    def on_enter(self):
        for room_item in self.selectedItems():
            self.on_room_item_activated(room_item, 1)
            break

    @ttk.pyTTkSlot(str)
    def on_search(self, text):

        text = str(text).lower()

        for room_name, room_item in self.room_items.items():  # invisibleRootItem().children():
            room_item.setHidden(text and text not in room_name.lower())

        self.window.setTitle(
            _("Search rooms…") if any(room_item.isHidden() for room_item in self.room_items.values()) else "All Rooms"
        )

        if text and all(room_item.isHidden() for room_item in self.room_items.values()):
            self.search_clear.setText(ttk.TTkString("⊀", ttk.TTkColor.BLINKING))  # ⊀≉
        else:
            self.search_clear.setText("<")

    @ttk.pyTTkSlot()
    def on_search_clear(self):
        self.search_entry.setText(ttk.TTkString(""))
        if self.window is not None:
            self.search_entry.setFocus()

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_room_item_activated(self, room_item, _column):
        core.chatrooms.show_room(room_item.name())
        self.window.close()

    def mouseEvent(self, evt):

        ret = super().mouseEvent(evt)

        if evt.evt == ttk.TTkK.Press:
            if self.popup_menu is not None:
                self.popup_menu.close()
                self.popup_menu = None

            if evt.key == ttk.TTkK.RightButton:
                room_item = self.itemAt(evt.y)

                if room_item is None:
                    return False

                self.create_popup_menu(room_item)
                self.popup_menu.popup(evt.x, evt.y)

        return ret

    def create_popup_menu(self, room_item):

        room = room_item.name()
        is_owner = core.chatrooms.is_room_owner(room)
        is_member = core.chatrooms.is_room_member(room)  # room_item.is_private
        is_joined = room in core.chatrooms.joined_rooms

        self.popup_menu = PopupMenu(self, title=room)  # parent=self.room_list

        self.popup_menu.addMenu(_("_Join Room"), name="join", data=room)
        self.popup_menu.join.setEnabled(not is_joined)
        self.popup_menu.join.menuButtonClicked.connect(self.on_popup_join)

        self.popup_menu.addMenu(_("_Leave Room"), name="leave", data=room)
        self.popup_menu.leave.setEnabled(is_joined)
        self.popup_menu.leave.menuButtonClicked.connect(self.on_popup_leave)

        self.popup_menu.addSpacer()

        self.popup_menu.addMenu(_("Delete Private Room…"), name="disown", data=room)
        self.popup_menu.disown.setEnabled(is_owner)
        self.popup_menu.disown.menuButtonClicked.connect(self.on_popup_delete_private_room)

        self.popup_menu.addMenu(_("Cancel Room Membership"), name="cancel", data=room)
        self.popup_menu.cancel.setEnabled(is_member and not is_owner)
        self.popup_menu.cancel.menuButtonClicked.connect(self.on_popup_cancel_room_membership)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_popup_join(self, button):
        core.chatrooms.show_room(button.data())
        self.window.close()

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_popup_leave(self, button):
        core.chatrooms.remove_room(button.data())

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_popup_delete_private_room(self, button):

        def response(_dialog, _button, room):
            core.chatrooms.request_cancel_room_ownership(room)

        OptionDialog(
            parent=self.screen,
            title=_("Delete Private Room?"),
            message=_("Do you really want to permanently delete your private room %s?") % f'\n"{button.data()}"',
            buttons=[
                (OptionDialog.StandardButton.Cancel, _("_Cancel")),
                (OptionDialog.StandardButton.Ok, _("Delete"))
            ],
            default_button=OptionDialog.StandardButton.Cancel,
            destructive_button=OptionDialog.StandardButton.Ok,
            callback=response,
            callback_data=button.data()
        ).present()

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_popup_cancel_room_membership(self, button):
        core.chatrooms.request_cancel_room_membership(button.data())


class RoomItem(ttk.TTkTreeWidgetItem):

    def __init__(self, data, is_private, style, icon=None):

        self._room_name = data[0]
        self.user_count = data[1]
        self.is_private = is_private

        data[0] = ttk.TTkString(self._room_name, style)
        data[1] = f"{self.user_count:6d}"  # humanize(self.user_count)

        super().__init__(data, icon=icon)

        #self._alignment = [ttk.TTkK.LEFT_ALIGN, ttk.TTkK.RIGHT_ALIGN]
        #self.setTextAlignment(1, ttk.TTkK.RIGHT_ALIGN)

    def name(self):
        return self._room_name

    def setData(self, column, value, emit=True):

        if column == 1:
            if value == self.user_count:
                return

            self.user_count = value
            value = f"{self.user_count:6d}"  # humanize(self.user_count)

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

        # Natural alphanumeric sort
        parts, c = [], ''
        for char in str(self.data(col)):
            if char.isdigit() == c.isdigit():
                c += char
            else:
                parts.append(c)
                c = char
        parts.append(c)

        return (_privateRoomsTop(), [int(part) if part.isdigit() else part.lower() for part in parts])
