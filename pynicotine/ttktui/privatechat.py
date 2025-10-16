# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2007 gallows <g4ll0ws@gmail.com>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.widgets.chatter import Chatter
from pynicotine.ttktui.widgets.menus import UserPopupMenu
from pynicotine.ttktui.widgets.pages import Pages
from pynicotine.ttktui.widgets.theme import USER_STATUS_COLORS


class PrivateChats(Pages):

    def __init__(self, screen, name="private"):

        self.screen = screen

        super().__init__(self, name)

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        _expander_left = ttk.TTkSpacer(parent=self.header_bar)

        self.username_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(">", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
        )
        self.username_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.username_button.clicked.connect(self.on_username_clicked)

        self.username_entry = ttk.TTkLineEdit(parent=self.header_bar, hint=_("Username…"))
        self.username_entry.setMinimumWidth(core.users.USERNAME_MAX_LENGTH)
        self.username_entry.setMaximumWidth(core.users.USERNAME_MAX_LENGTH)
        self.username_entry.returnPressed.connect(self.on_username_pressed)

        _gap = ttk.TTkSpacer(parent=self.header_bar, minWidth=1, maxWidth=1)

        self.private_history_button = ttk.TTkButton(parent=self.header_bar, text=ttk.TTkString("Chat History"))
        self.private_history_button.setMinimumWidth(self.private_history_button.text().termWidth()+4)
        self.private_history_button.setMaximumWidth(self.private_history_button.text().termWidth()+4)
        self.private_history_button.clicked.connect(screen.application.on_chat_history)

        _expander_right = ttk.TTkSpacer(parent=self.header_bar)

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout())
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[name]
        )
        _placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN,
            text=_("Enter the name of a user to start a conversation with them in private")
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        for widget in [self.username_button, self.username_entry]:
            widget.setToolTip(_placeholder.text())

        self.popup_menu = None
        self.highlighted_users = []

        for event_name, callback in (
            ("clear-private-messages", self.clear_messages),
            ("echo-private-message", self.echo_private_message),
            ("message-user", self.message_user),
            # ("private-chat-completions", self.update_completions),
            ("private-chat-show-user", self.show_user),
            ("private-chat-remove-user", self.remove_user),
            ("quit", self.quit),
            ("server-disconnect", self.server_disconnect),
            ("server-login", self.server_login),
            # ("start", self.start),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def quit(self):
        self.private_history_button.clicked.disconnect(self.screen.application.on_chat_history)
        self.username_button.clicked.disconnect(self.on_username_clicked)
        self.username_entry.returnPressed.disconnect(self.on_username_pressed)
        self.username_entry.clearFocus()
        self.username_entry.close()
        super().destroy()

    def focus_default_widget(self):

        page = self.currentWidget()

        if isinstance(page, Chatter) and page.chat_line.isEnabled():
            page.chat_line.setFocus()
        else:
            self.clearFocus()
            self.username_entry.setFocus()

    #@ttk.pyTTkSlot(ttk.TTkWidget, ttk.TTkMouseEvent)
    #def on_page_menu(self, page_button, evt):

    #    if self.popup_menu is not None:
    #        self.popup_menu._remove_page.menuButtonClicked.clear()
    #        self.popup_menu._remove_page.close()
    #        self.popup_menu.close()

    #    page = self.pages.get(page_button.data())

    #    if not page:
    #        self.focus_default_widget()
    #        return

    #    self.popup_menu = UserPopupMenu(page_button.parentWidget().parentWidget(), page.name())  # , "privatechat")
    #    self.popup_menu.addSpacer()
    #    self.popup_menu._remove_page = self.popup_menu.addMenu("  " + _("_Close Tab"))
    #    self.popup_menu._remove_page.menuButtonClicked.connect(page.on_close)
    #    self.popup_menu.popup(page_button.x()+evt.x, page_button.y()+1)

    @ttk.pyTTkSlot(int)
    def on_switch_page(self, page_number):

        if self.screen.tab_bar.currentWidget() != self:
            return

        page = self.widget(page_number)

        if not page:
            self.focus_default_widget()
            return

        page.load(is_enabled=core.users.login_username is not None)

        # Remove highlight if selected tab belongs to a user in the list of highlights
        self.unhighlight_user(page.name())
        self.remove_tab_changed(page)

    @ttk.pyTTkSlot()  # Enter
    def on_username_pressed(self):
        self.on_get_page(self.username_entry)

    @ttk.pyTTkSlot()  # Mouse
    def on_username_clicked(self):

        if not self.username_entry.text():
            self.username_entry.setFocus()
            return

        self.on_get_page(self.username_entry)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_get_page(self, caller):

        if isinstance(caller, ttk.TTkMenuButton):
            username = caller.data()
        else:
            username = str(caller.text()).strip()
            caller.setText("")

        if not username:
            return

        core.privatechat.show_user(username)

    def on_remove_all_pages(self, *_args):
        core.privatechat.remove_all_users()

    def on_restore_removed_page(self, page_args):
        username, = page_args
        core.privatechat.show_user(username)

    def clear_messages(self, user):

        page = self.pages.get(user)

        if page is not None:
            page.chat_view.clear()

    def clear_notifications(self):

        if self.screen.tab_bar.currentWidget() != self:
            return

        user = self.currentWidget().name()

        # Remove highlight
        self.unhighlight_user(user)

    def user_status(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            self.set_user_status(msg.user, msg.status)
            page.user_status(msg.status)

    def show_user(self, user, switch_page=True, remembered=False):

        if user not in self.pages:
            page_position = self.count() if remembered else 0

            self.pages[user] = page = PrivateChat(self, user)
            page_index = self.insertTab(page_position, page, f"   {user}", data=user)
            page_button = self.tabButton(page_index)
            page_button.closeClicked.connect(page.on_close)
            #page_button.rightButtonClicked.connect(self.on_page_menu)

            user_status = core.users.statuses.get(user, UserStatus.OFFLINE)
            self.set_user_status(user, user_status)
            page.user_status(user_status)

            self.update_pages_menu_item(user)
            self.update_pages_count()

        if switch_page:
            self.setCurrentWidget(self.pages[user])
            self.screen.tab_bar.setCurrentWidget(self.screen.tabs["private"])

    def remove_user(self, user):

        page = self.pages.get(user)

        if page is None:
            return

        self.remove_page(page, page_args=(user,))

    def highlight_user(self, user):

        if not user or user in self.highlighted_users:
            return

        self.highlighted_users.append(user)
        #self.window.update_title()  ##

    def unhighlight_user(self, user):

        if user not in self.highlighted_users:
            return

        self.highlighted_users.remove(user)
        #self.window.update_title()  ##

    def echo_private_message(self, user, text, message_type):

        page = self.pages.get(user)

        if page is not None:
            page.echo_message(text, message_type)

    def message_user(self, msg, **_unused):

        page = self.pages.get(msg.user)

        if page is not None:
            page.message_user(msg)

    def update_widgets(self):

        for tab in self.pages.values():
            tab.toggle_chat_buttons()

    def server_login(self, msg):

        if not msg.success:
            return

        for page in self.pages.values():
            if page != self.currentWidget():
                continue

            page.load(is_enabled=True)
            break

    def server_disconnect(self, *_args):

        for user, page in self.pages.items():
            for widget in [page.chat_send, page.chat_emoj, page.chat_line]:
                widget.setEnabled(False)

            page.offline_message = False
            self.set_user_status(user, UserStatus.OFFLINE)


class PrivateChat(Chatter):

    def __init__(self, chats, user):
        super().__init__(
            chats,
            user,
            send_message_callback=core.privatechat.send_message,
            command_callback=core.pluginhandler.trigger_private_chat_command_event,
            follow=True
        )
        self.offline_message = False

    @ttk.pyTTkSlot()
    def on_close(self, *_args):
        core.privatechat.remove_user(self.name())

    def clear(self):
        self.chat_view.clear()
        self.chats.unhighlight_user(self.name())

    def user_status(self, status):
        self.chat_send.mergeStyle({'default': {'color': USER_STATUS_COLORS.get(status).invertFgBg()}})

    def _show_notification(self, text, is_mentioned=False):

        is_buddy = (self.name() in core.buddies.users)

        self.chats.request_tab_changed(self, is_important=is_buddy or is_mentioned)

        if self.chats.currentWidget() == self and self.chats.screen.tab_bar.currentWidget() == self.chats:
            # Don't show notifications if the chat is open and the window is in use
            return

        self.chats.highlight_user(self.name())

        if config.sections["notifications"]["notification_popup_private_message"]:
            core.notifications.show_private_chat_notification(
                self.name(), text,
                title=_("Private Message from %(user)s") % {"user": self.name()}
            )

    def message_user(self, msg):

        is_outgoing_message = (msg.message_id is None)
        is_new_message = msg.is_new_message
        message_type = msg.message_type

        username = msg.user
        tag_username = (core.users.login_username if is_outgoing_message else username)

        timestamp = msg.timestamp if not is_new_message else None
        timestamp_format = config.sections["logging"]["private_timestamp"]
        message = msg.message

        if not is_outgoing_message:
            self._show_notification(message, is_mentioned=(message_type == "hilite"))

        if not is_outgoing_message and not is_new_message:
            if not self.offline_message:
                self.add_line(
                    _("* Messages sent while you were offline"), message_type="hilite",
                    timestamp_format=timestamp_format
                )
                self.offline_message = True

        else:
            self.offline_message = False

        self.add_line(
            message, message_type=message_type, timestamp=timestamp, timestamp_format=timestamp_format,
            username=tag_username
        )

        #self.chats.screen.application.chat_history.update_user(username, message)
        #if ttk.TTkString(username) not in self.chats.username_combobox.list:
        #    self.chats.username_combobox.addItem(ttk.TTkString(username))
