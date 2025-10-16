# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2016 Mutnick <muhing@yahoo.com>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2007 gallows <g4ll0ws@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import time

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.slskmessages import UserData
from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.widgets.chatter import Chatter
from pynicotine.ttktui.widgets.dialogs import OptionDialog
from pynicotine.ttktui.widgets.pages import Pages
from pynicotine.ttktui.widgets.theme import USER_STATUS_COLORS
from pynicotine.ttktui.widgets.trees import UsersList


class ChatRooms(Pages):

    def __init__(self, screen, name="chatrooms"):

        self.screen = screen

        super().__init__(self, name)

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        _expander_left = ttk.TTkSpacer(parent=self.header_bar)

        self.join_room_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(">", ttk.TTkColor.BOLD),  # ⎆
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
        )
        self.join_room_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.join_room_button.clicked.connect(self.on_join_room_clicked)

        self.chatrooms_entry = ttk.TTkLineEdit(parent=self.header_bar, hint=_("Join or create room…"))  # editable=True)  # , alignment=ttk.TTkK.CENTER_ALIGN)  #, minWidth=30)
        self.chatrooms_entry.setMinimumWidth(core.chatrooms.ROOM_NAME_MAX_LENGTH)
        self.chatrooms_entry.setMaximumWidth(core.chatrooms.ROOM_NAME_MAX_LENGTH)
        self.chatrooms_entry.returnPressed.connect(self.on_chatrooms_entry_pressed)

        _gap = ttk.TTkSpacer(parent=self.header_bar, minWidth=1, maxWidth=1)

        self.chatrooms_button = ttk.TTkButton(parent=self.header_bar, text=ttk.TTkString("All Rooms"))
        #self.chatrooms_button.setFocusPolicy(ttk.TTkK.FocusPolicy.StrongFocus)
        self.chatrooms_button.setMinimumWidth(self.chatrooms_button.text().termWidth()+4)
        self.chatrooms_button.setMaximumWidth(self.chatrooms_button.text().termWidth()+4)
        self.chatrooms_button.clicked.connect(screen.application.on_room_list)

        _expander_right = ttk.TTkSpacer(parent=self.header_bar)

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout())
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[name]
        )
        _placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN,
            text=_("Join a room to chat with other online users, "
                   "or create a private room with restricted access").replace(", ", ",\n")
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        for widget in [self.join_room_button, self.chatrooms_entry, self.chatrooms_button]:
            widget.setToolTip(_placeholder.text())

        self.popup_menu = None
        self.highlighted_rooms = {}

        for event_name, callback in (
            #("add-room-member", self.add_room_member),
            #("add-room-operator", self.add_room_operator),
            ("clear-room-messages", self.clear_room_messages),
            ("echo-room-message", self.echo_room_message),
            ("global-room-message", self.global_room_message),
            ("ignore-user", self.ignore_user),
            ("ignore-user-ip", self.ignore_user),
            ("join-room", self.join_room),
            ("leave-room", self.leave_room),
            ("peer-address", self.peer_address),
            ("quit", self.quit),
            ("remove-room", self.remove_room),
            ("remove-room-member", self.remove_room_member),
            #("remove-room-operator", self.remove_room_operator),
            #("room-membership-granted", self.room_membership_granted),
            #("room-membership-revoked", self.room_membership_revoked),
            #("room-operatorship-granted", self.room_operatorship_granted),
            #("room-operatorship-revoked", self.room_operatorship_revoked),
            #("room-ticker-added", self.room_ticker_added),
            #("room-ticker-removed", self.room_ticker_removed),
            #("room-completions", self.update_completions),
            #("room-list", self.room_list),
            ("say-chat-room", self.say_chat_room),
            ("server-disconnect", self.server_disconnect),
            ("show-room", self.show_room),
            #("start", self.start),
            ("unignore-user", self.unignore_user),
            ("unignore-user-ip", self.unignore_user),
            ("user-country", self.user_country),
            ("user-joined-room", self.user_joined_room),
            ("user-left-room", self.user_left_room),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def quit(self):
        self.join_room_button.clicked.disconnect(self.on_join_room_clicked)
        self.chatrooms_button.clicked.disconnect(self.screen.application.on_room_list)
        self.chatrooms_entry.returnPressed.disconnect(self.on_chatrooms_entry_pressed)
        self.chatrooms_entry.close()
        super().destroy()

    def focus_default_widget(self):

        if self.screen.tab_bar.currentWidget() != self:
            return

        page = self.currentWidget()

        if isinstance(page, Chatter) and page.chat_line.isEnabled():
            page.chat_line.setFocus()
        else:
            self.clearFocus()
            self.chatrooms_entry.setFocus()

    @ttk.pyTTkSlot(ttk.TTkWidget, ttk.TTkMouseEvent)
    def on_page_menu(self, page_button, evt):

        if self.popup_menu is not None:
            self.popup_menu._remove_page.menuButtonClicked.clear()
            self.popup_menu._remove_page.close()
            self.popup_menu.close()

        page = self.pages.get(page_button.data())

        if not page:
            self.focus_default_widget()
            return

        self.popup_menu = ttk.TTkMenu(parent=page_button.parentWidget())
        self.popup_menu._remove_page = self.popup_menu.addMenu(_("_Leave Room"))
        self.popup_menu._remove_page.menuButtonClicked.connect(page.on_close)
        #popup_menu.popup(page_button.x() + evt.x, page_button.y() + evt.y)
        ttk.TTkHelper.overlay(
            self.popup_menu.parentWidget(), self.popup_menu, page_button.x()+evt.x, page_button.y()+evt.y+1
        )

    @ttk.pyTTkSlot(int)
    def on_switch_page(self, page_number):

        if self.screen.tab_bar.currentWidget() != self:
            return

        page = self.widget(page_number)

        if not page:
            self.focus_default_widget()
            return

        joined_room = core.chatrooms.joined_rooms.get(page.name())

        page.load(is_enabled=joined_room is not None and joined_room.users and not page.is_global)

        self.unhighlight_room(page.name())
        self.remove_tab_changed(page)

    @ttk.pyTTkSlot()  # Enter
    def on_chatrooms_entry_pressed(self):
        self.on_get_page(self.chatrooms_entry)

    @ttk.pyTTkSlot()  # Mouse
    def on_join_room_clicked(self):

        if not self.chatrooms_entry.text():
            self.chatrooms_entry.setFocus()
            return

        self.on_get_page(self.chatrooms_entry)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_get_page(self, caller):

        if isinstance(caller, ttk.TTkMenuButton):
            room = caller.data()
        else:
            room = str(caller.text()).strip()
            caller.setText("")

        self.on_create_room(room)

    def on_create_room(self, room):

        if not room:
            return

        def response(dialog, _button, room):
            private = dialog.get_option_value()
            core.chatrooms.show_room(room, private)

        if (core.users.login_status != UserStatus.OFFLINE and room != core.chatrooms.GLOBAL_ROOM_NAME
                and room not in core.chatrooms.server_rooms and room not in core.chatrooms.private_rooms):
            room = core.chatrooms.sanitize_room_name(room)
            OptionDialog(
                parent=self.screen,
                title=_("Create New Room?"),
                message=_('Do you really want to create a new room "%s"?') % room,
                option_label=_("Make room private"),
                buttons = [
                    (OptionDialog.StandardButton.No, _("_Cancel")),
                    (OptionDialog.StandardButton.Yes, _("Cre_ate"))
                ],
                callback=response,
                callback_data=room
            ).present()
        else:
            core.chatrooms.show_room(room)

    def on_remove_all_pages(self, *_args):
        core.chatrooms.remove_all_rooms()

    def on_restore_removed_page(self, page_args):
        room, is_private = page_args
        core.chatrooms.show_room(room, is_private=is_private)

    def clear_room_messages(self, room):

        page = self.pages.get(room)

        if page is not None:
            page.clear()

    def show_room(self, room, is_private=False, switch_page=True, remembered=False):

        if room not in self.pages:
            is_global = (room == core.chatrooms.GLOBAL_ROOM_NAME)
            page_position = 0 if is_global and not remembered else self.count()

            self.pages[room] = page = ChatRoom(self, room, is_private=is_private, is_global=is_global)
            page_index = self.insertTab(page_position, page, f"  {room} ", data=room)
            page_button = self.tabButton(page_index)
            page_button.closeClicked.connect(page.on_close)
            #page_button.rightButtonClicked.connect(self.on_page_menu)

            self.update_page_tab_button(room)
            self.update_pages_menu_item(room)
            self.update_pages_count()

            #if not is_global:
            #    combobox = self.window.search.room_search_combobox
            #    combobox.append(room)

        if switch_page:
            self.screen.tab_bar.setCurrentWidget(self.screen.tabs["chatrooms"])
            self.setCurrentWidget(self.pages[room])

    def remove_room(self, room):

        page = self.pages.get(room)

        if page is None:
            return

        self.remove_page(page, page_args=(room, page.is_private))

        #if room != core.chatrooms.GLOBAL_ROOM_NAME:
        #    combobox = self.window.search.room_search_combobox
        #    combobox.remove_id(room)

    def highlight_room(self, room, user):

        if not room or room in self.highlighted_rooms:
            return

        self.highlighted_rooms[room] = user
        # self.window.update_title()

    def unhighlight_room(self, room):

        if room not in self.highlighted_rooms:
            return

        del self.highlighted_rooms[room]
        # self.window.update_title()

    def join_room(self, msg):

        page = self.pages.get(msg.room)
        # self.join_room_combobox.append(msg.room)

        if page is None:
            return

        page.join_room(msg)

    def leave_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.leave_room()

    def ignore_user(self, username, *_args):
        for page in self.pages.values():
            page.ignore_user(username)

    def unignore_user(self, username, *_args):
        for page in self.pages.values():
            page.unignore_user(username)

    def peer_address(self, msg):
        for page in self.pages.values():
            page.peer_address(msg)

    def user_stats(self, msg):
        for page in self.pages.values():
            page.user_stats(msg)

    def user_status(self, msg):
        for page in self.pages.values():
            page.user_status(msg.user, msg.status)

    def user_country(self, user, country):
        for page in self.pages.values():
            page.user_country(user, country)

    def user_joined_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.user_joined_room(msg)

    def user_left_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.user_left_room(msg)

    def remove_room_member(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.remove_room_member(msg)

    def echo_room_message(self, room, text, message_type):

        page = self.pages.get(room)

        if page is not None:
            page.echo_message(text, message_type)

    def say_chat_room(self, msg):

        page = self.pages.get(msg.room)

        if page is not None:
            page.say_chat_room(msg)

    def global_room_message(self, msg):

        page = self.pages.get(core.chatrooms.GLOBAL_ROOM_NAME)

        if page is not None:
            page.global_room_message(msg)

    def update_widgets(self):

        #self.chat_entry.set_spell_check_enabled(config.sections["ui"]["spellcheck"])

        for tab in self.pages.values():
            tab.toggle_chat_buttons()
            # tab.update_tags()

    def server_disconnect(self, *_args):
        for page in self.pages.values():
            page.leave_room()


class ChatRoom(Chatter):

    def __init__(self, chats, room, is_private, is_global):
        super().__init__(
            chats,
            room,
            send_message_callback=core.chatrooms.send_message,
            command_callback=core.pluginhandler.trigger_chatroom_command_event,
            follow=True
        )

        self.is_private = is_private
        self.is_global = is_global

        self.users_list = RoomUsersList(parent=self.users_container)  # , room=room)
        self.unread_room_wall_users = set()

        if self.is_global:
            self.chat_line.setEnabled(False)
            self.chat_send.setEnabled(False)
            self.chat_emoj.setEnabled(False)
            return

        self.user_list_button = ttk.TTkButton(
            parent=self.chat_bar, text="◨", checkable=True, checked=False, minWidth=3, maxWidth=3
        )
        self.user_list_button.toggled.connect(self.on_toggle_user_list_visibility)
        self.user_list_button.setChecked(config.sections["chatrooms"]["user_list_visible"])

    @ttk.pyTTkSlot()
    def on_close(self, *_args):
        core.chatrooms.remove_room(self.name())

    def destroy(self):
        self.clear()
        if not self.is_global:
            self.users_list.clear()
            self.users_list.close()
            #self.users_container.layout().removeWidget(self.users_list)
            self.layout().removeWidget(self.users_container)
        super().destroy()

    def clear(self):

        self.chat_view.clear()

        if self.activity_view:
            self.activity_view.clear()

        self.chats.unhighlight_room(self.name())

    def add_user_row(self, userdata):  # , username_color=None):

        username = userdata.username

        old_user_item = self.users_list.iterators.get(username)

        if old_user_item is not None:
            self.users_list.remove_user_item(old_user_item)

        private_room = core.chatrooms.private_rooms.get(self.name())
        _user_item = self.users_list.add_row(self._generate_user_row(userdata, private_room=private_room))

    def _generate_user_row(self, userdata, private_room=None):

        username = userdata.username

        return [
            userdata.status,
            ttk.TTkString(username, self.users_list.get_username_color(username, private_room=private_room)),
            userdata.files,
            userdata.country  # flag_icon_name = get_flag_icon_name(userdata.country)
            #userdata.avgspeed,
            #userdata.dirs
        ]

    def populate_room_users(self, joined_users):

        private_room = core.chatrooms.private_rooms.get(self.name())

        # Add batch of user items in a single paint for increased performance
        self.users_list.add_rows(
            self._generate_user_row(user_data, private_room=private_room)
            for user_data in joined_users if user_data.username not in self.users_list.iterators
        )

        # List private room members who are offline/not currently joined
        if private_room is not None:
            owner = private_room.owner

            self.users_list.add_rows(
                self._generate_user_row(UserData(username, status=UserStatus.OFFLINE), private_room=private_room)
                for username in private_room.members if username not in self.users_list.iterators
            )

        self.update_user_count()
        self.users_list.resizeColumnToContents(3)  # Co

        # Update all username tags in chat log
        # self.chat_view.update_user_tags()

    def join_room(self, msg):

        if self.is_global:
            return

        self.is_private = msg.private

        if self == self.chats.currentWidget():
            for widget in [self.chat_send, self.chat_emoj, self.chat_line]:
                widget.setEnabled(True)

            self.chats.focus_default_widget()

        self.activity_view.append(self.get_timestamp() + " " + _("%s joined the room") % core.users.login_username)
        self.populate_room_users(msg.users)
        self.user_status(core.users.login_username, core.users.login_status)

    def leave_room(self):

        if not self.is_global:
            self.users_list.clear()
            self.update_user_count()
            # self.chat_view.update_user_tags()

            if core.users.login_status == UserStatus.OFFLINE:
                leave_message = _("--- disconnected ---")
            else:
                leave_message = _("%s left the room") % core.users.login_username

            self.activity_view.append(self.get_timestamp() + " " + leave_message)

        for widget in [self.chat_send, self.chat_emoj, self.chat_line]:
            widget.setEnabled(False)

        if self == self.chats.currentWidget():
            self.chats.focus_default_widget()

    def update_user_count(self):
        self.users_header.setTitle(
            f'{len(self.users_list.iterators)} {_("Members") if self.is_private else _("Users")}')

    def get_timestamp(self, timestamp_format=None, timestamp=None):
        return time.strftime(
            timestamp_format or config.sections["logging"]["rooms_timestamp"], time.localtime(timestamp))

    def ignore_user(self, username):

        user_item = self.users_list.iterators.get(username)

        if user_item is None:
            return

        private_room = core.chatrooms.private_rooms.get(self.name())
        user_item.setData(
            1, ttk.TTkString(username, self.users_list.get_username_color(username, private_room=private_room)).toAnsi()
        )

    def unignore_user(self, username):

        user_item = self.users_list.iterators.get(username)

        if user_item is None:
            return

        private_room = core.chatrooms.private_rooms.get(self.name())
        user_item.setData(
            1, ttk.TTkString(username, self.users_list.get_username_color(username, private_room=private_room)).toAnsi()
        )

    def peer_address(self, msg):

        username = msg.user

        if username not in self.users_list.iterators or not core.network_filter.is_user_ip_ignored(username):
            return

        self.ignore_user(username)

    def user_stats(self, msg):

        user = msg.user
        user_item = self.users_list.iterators.get(user)

        if user_item is None:
            return

        if user not in core.chatrooms.joined_rooms[self.name()].users:
            # Private room member offline/not currently joined
            return

        user_item.setData(4, msg.avgspeed, emit=False)
        user_item.setData(2, msg.files)

    def user_status(self, user, status):

        user_item = self.users_list.iterators.get(user)

        if user_item is None:
            return

        if user == core.users.login_username:
            self.chat_send.mergeStyle({'default': {'color': USER_STATUS_COLORS.get(status).invertFgBg()}})

        if user not in core.chatrooms.joined_rooms[self.name()].users:
            # Private room member offline/not currently joined
            return

        if status and status == user_item.status:  # (iterator, "status"):
            return

        if status == UserStatus.AWAY:
            action = _("%s has gone away")

        elif status == UserStatus.ONLINE:
            action = _("%s has returned")

        else:
            # If we reach this point, the server did something wrong. The user should have
            # left the room before an offline status is sent.
            return

        if not core.network_filter.is_user_ignored(user) and not core.network_filter.is_user_ip_ignored(user):
            self.activity_view.append(self.get_timestamp() + " " + action % user)

        user_item.setData(0, status)  # , emit=False)

        # self.chat_view.update_user_tag(user)

    def user_country(self, user, country_code):

        user_item = self.users_list.iterators.get(user)

        if user_item is None:
            return

        if user not in core.chatrooms.joined_rooms[self.name()].users:
            # Private room member offline/not currently joined
            return

        user_item.setData(3, country_code)  # flag_icon_name = get_flag_icon_name(country_code)

    def user_joined_room(self, msg):

        userdata = msg.userdata
        username = userdata.username
        user_item = self.users_list.iterators.get(username)

        if user_item is not None:
            if not self.is_private:
                return

            self.users_list.remove_user_item(user_item)

        if (username != core.users.login_username
                and not core.network_filter.is_user_ignored(username)
                and not core.network_filter.is_user_ip_ignored(username)):
            self.activity_view.append(self.get_timestamp() + " " + _("%s joined the room") % username)

        self.add_user_row(userdata)

        # self.chat_view.update_user_tag(username)
        self.update_user_count()

    def user_left_room(self, msg):

        username = msg.username
        user_item = self.users_list.iterators.get(username)

        if user_item is None:
            return

        if not core.network_filter.is_user_ignored(username) and not core.network_filter.is_user_ip_ignored(username):
            self.activity_view.append(self.get_timestamp() + " " + _("%s left the room") % username)

        if self.is_private:
            user_item.setData(3, "", emit=False)  # country
            user_item.setData(4, 0, emit=False)  # h_speed, speed
            user_item.setData(2, 0, emit=False)  # h_files, files
            user_item.setData(0, UserStatus.OFFLINE)
        else:
            self.users_list.remove_user_item(user_item)

        # self.chat_view.update_user_tag(username)
        self.update_user_count()

    def remove_room_member(self, msg):

        username = msg.user
        user_item = self.users_list.iterators.get(username)

        if user_item is None:
            return

        self.users_list.remove_user_item(user_item)

        # self.chat_view.update_user_tag(username)
        self.update_user_count()

    def _show_notification(self, room, user, text, is_mentioned):

        self.chats.request_tab_changed(self, is_important=is_mentioned, is_quiet=self.is_global)

        if self.is_global and room in core.chatrooms.joined_rooms:
            # Don't show notifications about the Public feed that's duplicated in an open tab
            return

        if is_mentioned:
            log.add(_("%(user)s mentioned you in room %(room)s") % {"user": user, "room": room})

            if config.sections["notifications"]["notification_popup_chatroom_mention"]:
                core.notifications.show_chatroom_notification(
                    room, text,
                    title=_("Mentioned by %(user)s in Room %(room)s") % {"user": user, "room": room},
                    high_priority=True
                )

        if self.chats.currentWidget() == self and self.chats.screen.tab_bar.currentWidget() == self.chats:
            # Don't show notifications if the chat is open and the window is in use
            return

        if is_mentioned:
            self.chats.highlight_room(room, user)
            return

        if not self.is_global and config.sections["notifications"]["notification_popup_chatroom"]:
            # Don't show notifications for public feed room, they're too noisy
            core.notifications.show_chatroom_notification(
                room, text,
                title=_("Message by %(user)s in Room %(room)s") % {"user": user, "room": room}
            )

    def say_chat_room(self, msg):

        roomname = msg.room
        username = msg.user
        message = msg.message
        message_type = msg.message_type

        if message_type != "local":
            self._show_notification(
                roomname, username, message, is_mentioned=(message_type == "hilite"))

        self.add_line(
            message, message_type=message_type, roomname=roomname if self.is_global else None, username=username,
            timestamp_format=config.sections["logging"]["rooms_timestamp"]
        )

    def global_room_message(self, msg):
        self.say_chat_room(msg)

    @ttk.pyTTkSlot(bool)
    def on_toggle_user_list_visibility(self, visible):

        if self.is_global:
            return

        config.sections["chatrooms"]["user_list_visible"] = visible
        tooltip = _("Hide Room Users") if visible else _("Show Room Users")

        self.user_list_button.setText("◫" if visible else "◨")
        self.user_list_button.setToolTip(tooltip)

        self.users_container.setVisible(visible)

        if visible and self.count() < 2:
            self.insertWidget(1, self.users_container, size=min(52, self.chats.screen.width() // 4))

        elif self.count() > 1:
            self.removeItem(self.users_container)

        self.chats.focus_default_widget()


class RoomUsersList(UsersList):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)

        #self.parent = parent
        #self.room = parent.parentWidget().name()

    @staticmethod
    def get_username_color(username, private_room=None):

        username_color = ttk.TTkColor.RST

        if core.network_filter.is_user_ignored(username) or core.network_filter.is_user_ip_ignored(username):
            username_color += ttk.TTkColor.fg("#888888")

        if private_room is not None:
            if username == private_room.owner:
                username_color += ttk.TTkColor.BOLD + ttk.TTkColor.UNDERLINE

            elif username in private_room.operators:
                username_color += ttk.TTkColor.BOLD

        return username_color

    def remove_user_item(self, user_item):

        user_index = self.indexOfTopLevelItem(user_item)
        old_user_item = self.takeTopLevelItem(user_index)

        #if user_item != old_user_item:
        #    raise KeyError(f"{user_item} is not {old_user_item}")

        del self.iterators[str(old_user_item.data(self._KEY_COLUMN))]

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_user_item_activated(self, user_item, _col):
        core.userinfo.show_user(str(user_item.data(self._KEY_COLUMN)))
