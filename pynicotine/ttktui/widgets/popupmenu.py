# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2009 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later


import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core


class UserPopupMenu(ttk.TTkMenu):

    def __init__(self, parent, username, tab_name, connect_events=True):
        super().__init__(parent=parent)  # , title=username)

        self.username = username
        self.tab_name = tab_name

        #if tab_name != "private_rooms":
        self.setup_user_menu(connect_events)

        self.closed.connect(self.destroy)

    def setup_user_menu(self, connect_events):

        #self.set_user(username)

        self._copy = self.addMenu(self.username)
        self._copy.menuButtonClicked.connect(self.on_copy_user)
        self.addSpacer()

        if self.tab_name != "userinfo":
            self._profile = self.addMenu("  " + _("View User _Profile"))
            self._profile.menuButtonClicked.connect(self.on_user_profile)
        else:
            self._profile = None

        if self.tab_name != "privatechat":
            self._message = self.addMenu("  " + _("_Send Message"))
            self._message.menuButtonClicked.connect(self.on_send_message)
        else:
            self._message = None

        if self.tab_name != "userbrowse":
            self._browse = self.addMenu("  " + _("_Browse Files"))
            self._browse.menuButtonClicked.connect(self.on_browse_user)
        else:
            self._browse = None

        if self.tab_name != "userlist":
            self._buddy = self.addMenu(_("_Add Buddy"), checkable=True)
        else:
            self._buddy = None

        self.addSpacer()
        self._ban_user = self.addMenu(_("Ban User"), checkable=True)
        self._ignore_user = self.addMenu(_("Ignore User"), checkable=True)
        self.addSpacer()
        self._ban_ip = self.addMenu(_("Ban IP Address"), checkable=True)
        self._ignore_ip = self.addMenu(_("Ignore IP Address"), checkable=True)
        self._show_ip = self.addMenu("  " + _("Show IP A_ddress"))
        self._show_ip.menuButtonClicked.connect(self.on_show_ip_address)

        #self.addSpacer()
        #self._private_rooms = self.addMenu(_("Private Rooms"))
        #self._private_rooms.menuButtonClicked.connect(self.popup_menu_private_rooms)

        if connect_events:
            self.connect_events()

    def connect_events(self):

        #self.editing = True

        local_username = core.users.login_username or config.sections["server"]["login"]

        if self._buddy is not None:
            self._buddy.toggled.disconnect(self.on_add_to_list)
            self._buddy.setChecked(self.username in core.buddies.users)
            self._buddy.toggled.connect(self.on_add_to_list)

        for menu_item, action, state in [
            (self._ban_user, self.on_ban_user, core.network_filter.is_user_banned(self.username)),
            (self._ignore_user, self.on_ignore_user, core.network_filter.is_user_ignored(self.username)),
            (self._ban_ip, self.on_ban_ip, core.network_filter.is_user_ip_banned(self.username)),
            (self._ignore_ip, self.on_ignore_ip, core.network_filter.is_user_ip_ignored(self.username))
        ]:
            menu_item.toggled.disconnect(action)

            # Disable menu item if it's our own username and we haven't banned ourselves before
            menu_item.setEnabled(self.username != local_username or state)
            menu_item.setChecked(state)

            menu_item.toggled.connect(action)

        #self.popup_menu_private_rooms.populate_private_rooms()
        #self.popup_menu_private_rooms.update_model()

        #self.actions[_("Private Rooms")].set_enabled(bool(self.popup_menu_private_rooms.items))
        #self.editing = False

    def destroy(self):

        for menu_item, action in [
            (self._copy, self.on_copy_user),
            (self._profile, self.on_user_profile),
            (self._message, self.on_send_message),
            (self._browse, self.on_browse_user),
            (self._show_ip, self.on_show_ip_address)
        ]:
            if menu_item is not None:
                menu_item.menuButtonClicked.disconnect(action)
                menu_item.close()  # self.removeMenuItem(menu_item)

        for menu_item, action in [
            (self._buddy, self.on_add_to_list),
            (self._ban_user, self.on_ban_user),
            (self._ignore_user, self.on_ignore_user),
            (self._ban_ip, self.on_ban_ip),
            (self._ignore_ip, self.on_ignore_ip),
        ]:
            if menu_item is not None:
                menu_item.toggled.disconnect(action)
                menu_item.close()  # self.removeMenuItem(menu_item)

        self.layout().clear()

    def popup(self, pos_x, pos_y):
        ttk.TTkHelper.overlay(self.parentWidget(), self, pos_x, pos_y)

    # Events #

    def on_copy_user(self, *_args):
        pass  ## clipboard.copy_text(self.username)

    def on_send_message(self, *_args):
        core.privatechat.show_user(self.username)

    def on_show_ip_address(self, *_args):
        core.users.request_ip_address(self.username, notify=True)

    def on_user_profile(self, *_args):
        core.userinfo.show_user(self.username)

    def on_browse_user(self, *_args):
        core.userbrowse.browse_user(self.username)

    @ttk.pyTTkSlot(bool)
    def on_add_to_list(self, state):
        if state:
            core.buddies.add_buddy(self.username)
        else:
            core.buddies.remove_buddy(self.username)

    @ttk.pyTTkSlot(bool)
    def on_ban_user(self, state):
        if state:
            core.network_filter.ban_user(self.username)
        else:
            core.network_filter.unban_user(self.username)

    @ttk.pyTTkSlot(bool)
    def on_ban_ip(self, state):
        if state:
            core.network_filter.ban_user_ip(self.username)
        else:
            core.network_filter.unban_user_ip(self.username)

    @ttk.pyTTkSlot(bool)
    def on_ignore_ip(self, state):
        if state:
            core.network_filter.ignore_user_ip(self.username)
        else:
            core.network_filter.unignore_user_ip(self.username)

    @ttk.pyTTkSlot(bool)
    def on_ignore_user(self, state):
        if state:
            core.network_filter.ignore_user(self.username)
        else:
            core.network_filter.unignore_user(self.username)
