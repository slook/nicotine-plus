# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
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
        canvas.drawMenuBarBg((0, 0), self.width(), color=self.classStyle['disabled']['color'])


class PopupMenu(ttk.TTkMenu):

    def __init__(self, parent, closed_callback=None, **kwargs):
        super().__init__(parent=parent, **kwargs)

        self.closed_callback = closed_callback
        self.closed.connect(self.destroy)

    def destroy(self):

        self.closed.disconnect(self.destroy)
        self.focusChanged.disconnect(self._on_focused)

        for button in self._get_menu_buttons():
            if button.isCheckable():
                button.toggled.clear()
            else:
                button.menuButtonClicked.clear()

            button.close()

        for spacer in self._scrollView._submenu:
            spacer.close()

        if self.closed_callback is not None:
            self.closed_callback()

        self.layout().clear()
        self.__dict__.clear()

    def _get_menu_buttons(self):
        for button in self.__dict__.values():
            if not isinstance(button, ttk.TTkMenuButton):
                continue
            yield button

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

        # self._scrollView._triggerSubmenu()
        ttk.TTkHelper.overlay(self.parentWidget(), self, pos_x, pos_y)

        self.focusChanged.connect(self._on_focused)

    def _on_focused(self, is_focused):
        if not is_focused and self.parentWidget().hasFocus():
            self.close()


class FilePopupMenu(PopupMenu):

    def __init__(self, parent, selected_files, closed_callback=None):

        self.module = parent.module
        self.selected_files = selected_files

        num_files = len(selected_files)
        count_label = ngettext("%(num)s File Selected", "%(num)s Files Selected", num_files) % {"num": num_files}

        super().__init__(parent=parent, name=self.module.name(), closed_callback=closed_callback, title=count_label)

        self._setup_file_menu(num_files)

    def _setup_file_menu(self, num_files):

        if not self.module.screen.application.isolated_mode:
            self.addMenu(_("_Open File") if num_files == 1 else _("_Open Files"), name="open_file")
            self.open_file.menuButtonClicked.connect(self.on_open_files)
            self.addMenu(_("Open in File _Manager"), name="open_file_manager")
            self.open_file_manager.menuButtonClicked.connect(self.on_open_file_manager)

        self.addMenu(_("F_ile Properties"), name="file_properties")  # , data=self.selected_files)
        # self.file_properties.menuButtonClicked.connect(on_file_properties)
        self.addMenu("", "sep1")
        self.addMenu(_("Re_sume") if self.module.name().startswith("download") else _("_Retry"), name="retry")
        self.retry.menuButtonClicked.connect(self.on_retry)
        self.addMenu(_("_Pause") if self.module.name().startswith("download") else _("_Abort"), name="abort")
        self.abort.menuButtonClicked.connect(self.on_abort)
        self.addMenu(_("Remove"), name="remove")
        self.remove.menuButtonClicked.connect(self.on_remove)
        self.addMenu("", "sep2")
        self.addMenu(_("_Browse Folder"), name="browse_folder")  # , data=next(iter(self.selected_files), None))
        self.browse_folder.menuButtonClicked.connect(self.on_browse_folder)

    def setup_users_menus(self, selected_user_items):

        self.addMenu(_("View User _Profile"), name="user_profile", data=selected_user_items)
        self.user_profile.menuButtonClicked.connect(self.on_user_profile)
        self.addMenu("", "sep3")
        self.addMenu(_("User Actions"), name="user_actions")

        for user_item in selected_user_items:
            if len(selected_user_items) > 1:
                # Multiple users, create submenus for each of them
                user_popup_button = self.user_actions.addMenu(user_item.username)
            else:
                # Single user, add items directly to "User Actions" submenu
                user_popup_button = self.user_actions

            user_menu = UserPopupMenu(self.parentWidget(), user_item)  # , closed_callback=self.closed_callback)
            user_menu.setup(user_popup_button)

            user_popup_button.addSpacer()
            user_select = user_popup_button.addMenu(_("Select User's Transfers"), data=user_item)
            user_select.menuButtonClicked.connect(self.on_user_select)

        if self.module.name().startswith("upload"):
            if len(selected_user_items) > 1:
                self.user_actions.addSpacer()

            abort_users = self.user_actions.addMenu(_("Abort _Users"), data=selected_user_items)
            abort_users.menuButtonClicked.connect(self.on_abort_users)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_open_files(self, button):
        self.module.open_files(self.selected_files)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_open_file_manager(self, button):
        self.module.open_file_manager(self.selected_files)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_browse_folder(self, button):
        selected_transfer = next(iter(self.selected_files))
        self.module.browse_folder(selected_transfer)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_user_profile(self, button):
        selected_user_items = button.data()
        self.module.user_profile(selected_user_items)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_user_select(self, button):
        selected_username = button.data().username
        self.module.select_user_transfers(selected_username)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_abort_users(self, button):
        selected_user_items = button.data()
        self.module.on_abort_users(selected_user_items)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_retry(self, button):
        self.module.retry_selected_transfers(self.selected_files)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_abort(self, button):
        self.module.abort_selected_transfers(self.selected_files)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_remove(self, button):
        self.module.remove_selected_transfers(self.selected_files)


class UserPopupMenu(PopupMenu):

    def __init__(self, parent, user_item, closed_callback=None):

        self.username = username = user_item if isinstance(user_item, str) else user_item.name()

        super().__init__(parent=parent, name=username, closed_callback=closed_callback)  # , title=username)

    def setup(self, menu):

        menu.copy = menu.addMenu(self.username)
        menu.copy.menuButtonClicked.connect(self.on_copy_user)
        menu.addSpacer()

        if self.parentWidget().name() != "userinfo":
            menu.profile = menu.addMenu(_("View User _Profile"))
            menu.profile.menuButtonClicked.connect(self.on_user_profile)

        if self.parentWidget().name() != "privatechat":
            menu.message = menu.addMenu(_("_Send Message"))
            menu.message.menuButtonClicked.connect(self.on_send_message)

        if self.parentWidget().name() != "userbrowse":
            menu.browse = menu.addMenu(_("_Browse Files"))
            menu.browse.menuButtonClicked.connect(self.on_browse_user)

        if self.parentWidget().name() != "userlist":
            menu.buddy = menu.addMenu(_("_Add Buddy"), checkable=True)
            menu.buddy.setChecked(self.username in core.buddies.users)
            menu.buddy.toggled.connect(self.on_add_to_list)

        menu.addSpacer()
        menu.ban_user = menu.addMenu(_("Ban User"), checkable=True)
        menu.ignore_user = menu.addMenu(_("Ignore User"), checkable=True)
        menu.addSpacer()
        menu.ban_ip = menu.addMenu(_("Ban IP Address"), checkable=True)
        menu.ignore_ip = menu.addMenu(_("Ignore IP Address"), checkable=True)
        menu.show_ip = menu.addMenu(_("Show IP A_ddress"))
        menu.show_ip.menuButtonClicked.connect(self.on_show_ip_address)

        if self.parentWidget().name() == "userlist":
            menu.note = menu.addMenu(_("Add User _Note…"))
            menu.note.menuButtonClicked.connect(self.parentWidget().parentWidget().on_add_note)
            menu.addSpacer()
            menu.remove_buddy = menu.addMenu(_("Remove"))
            menu.remove_buddy.menuButtonClicked.connect(self.parentWidget().parentWidget().on_remove_buddy)

        local_username = core.users.login_username or config.sections["server"]["login"]

        for menu_item, action, state in [
            (menu.ban_user, self.on_ban_user, core.network_filter.is_user_banned(self.username)),
            (menu.ignore_user, self.on_ignore_user, core.network_filter.is_user_ignored(self.username)),
            (menu.ban_ip, self.on_ban_ip, core.network_filter.is_user_ip_banned(self.username)),
            (menu.ignore_ip, self.on_ignore_ip, core.network_filter.is_user_ip_ignored(self.username))
        ]:
            # Disable menu item if it's our own username and we haven't banned ourselves before
            menu_item.setEnabled(self.username != local_username or state)
            menu_item.setChecked(state)
            menu_item.toggled.connect(action)

    # Events #

    def on_copy_user(self, *_args):
        pass  # clipboard.copy_text(self.username)

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
