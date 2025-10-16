# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2009 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later


import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core


class _MenuSpacer(ttk.TTkWidget):

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

    def paintEvent(self, canvas):
        canvas.drawMenuBarBg((0,0), self.width(), color=self.classStyle['disabled']['color'])


class PopupMenu(ttk.TTkMenu):

    def __init__(self, parent, **kwargs):
        super().__init__(parent=parent, **kwargs)

        self.closed.connect(self.destroy)

    def destroy(self):

        for button in self.__dict__.values():
            if not isinstance(button, ttk.TTkMenuButton):
                continue

            if button.isCheckable():
                button.toggled.clear()
            else:
                button.menuButtonClicked.clear()

            button.close()

        for spacer in self._scrollView._submenu:
            spacer.close()

        self.closed.disconnect(self.destroy)
        self.layout().clear()
        self.__dict__.clear()

    def addMenu(self, text, name=None, **kwargs):

        button = super().addMenu(text, **kwargs) if text else self.addSpacer()

        if name is not None:
            if name in self.__dict__:
                raise AttributeError(f'"{name}" already exists in {self}.{self.__dict__.keys()}')

            self.__dict__[name] = button

        return button

    def addSpacer(self):
        spacer = _MenuSpacer()
        self.addMenuItem(spacer)
        return spacer

    def popup(self, pos_x, pos_y):
        #self._scrollView._triggerSubmenu()
        ttk.TTkHelper.overlay(self.parentWidget(), self, pos_x, pos_y)


class UserPopupMenu(PopupMenu):

    def __init__(self, parent, user_item, connect_events=True):

        self.username = username = user_item if isinstance(user_item, str) else user_item.name()

        super().__init__(parent=parent, name=username)  # , title=username)

        self.addMenu(self.name(), name="copy")  # username
        self.copy.menuButtonClicked.connect(self.on_copy_user)
        self.addSpacer()

        if self.parentWidget().name() != "userinfo":
            self.addMenu(_("View User _Profile"), name="profile")
            self.profile.menuButtonClicked.connect(self.on_user_profile)

        if self.parentWidget().name() != "privatechat":
            self.addMenu(_("_Send Message"), name="message")
            self.message.menuButtonClicked.connect(self.on_send_message)

        if self.parentWidget().name() != "userbrowse":
            self.addMenu(_("_Browse Files"), name="browse")
            self.browse.menuButtonClicked.connect(self.on_browse_user)

        if self.parentWidget().name() != "userlist":
            self.addMenu(_("_Add Buddy"), name="buddy", checkable=True)
            self.buddy.setChecked(username in core.buddies.users)
            self.buddy.toggled.connect(self.on_add_to_list)

        self.addSpacer()
        self.addMenu(_("Ban User"), name="ban_user", checkable=True)
        self.addMenu(_("Ignore User"), name="ignore_user", checkable=True)
        self.addSpacer()
        self.addMenu(_("Ban IP Address"), name="ban_ip", checkable=True)
        self.addMenu(_("Ignore IP Address"), name="ignore_ip", checkable=True)
        self.addMenu(_("Show IP A_ddress"), name="show_ip")
        self.show_ip.menuButtonClicked.connect(self.on_show_ip_address)

        if self.parentWidget().name() == "userlist":
            self.addMenu(_("Add User _Note…"), name="note")
            self.note.menuButtonClicked.connect(parent.parentWidget().on_add_note)
            self.addSpacer()
            self.addMenu(_("Remove"), name="remove_buddy")
            self.remove_buddy.menuButtonClicked.connect(parent.parentWidget().on_remove_buddy)

        local_username = core.users.login_username or config.sections["server"]["login"]

        for menu_item, action, state in [
            (self.ban_user, self.on_ban_user, core.network_filter.is_user_banned(username)),
            (self.ignore_user, self.on_ignore_user, core.network_filter.is_user_ignored(username)),
            (self.ban_ip, self.on_ban_ip, core.network_filter.is_user_ip_banned(username)),
            (self.ignore_ip, self.on_ignore_ip, core.network_filter.is_user_ip_ignored(username))
        ]:
            # Disable menu item if it's our own username and we haven't banned ourselves before
            menu_item.setEnabled(username != local_username or state)
            menu_item.setChecked(state)
            menu_item.toggled.connect(action)

        self.closed.connect(self.destroy)

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
