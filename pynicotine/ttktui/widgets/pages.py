# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2009 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

import TermTk as ttk

from collections import deque

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.ttktui.widgets.dialogs import OptionDialog
# from pynicotine.gtkgui.widgets.theme import add_css_class
# from pynicotine.gtkgui.widgets.theme import remove_css_class
# from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.widgets.theme import TAB_COLORS
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS
from pynicotine.utils import humanize


class Pages(ttk.TTkTabWidget):

    def __init__(self, module, name):
        super().__init__(border=False, closable=True, name=name)

        self.screen = module.screen
        self.module = module

        self.pages = {}
        self.unread_pages = {}
        self.recently_removed_pages = deque(maxlen=5)  # Low limit to prevent excessive server traffic
        self.header_bar = None

        self.menu = self.addMenu(" 0 ", position=ttk.TTkK.RIGHT)
        self.menu.widgets = {}

        self.menu._reopen = self.menu.addMenu(_("Re_open Closed Tab"))
        self.menu._reopen.menuButtonClicked.connect(self.restore_removed_page)
        self.menu._reopen.setEnabled(False)

        self.menu._closeall = self.menu.addMenu(_("Close All Tabs…"))
        self.menu._closeall.menuButtonClicked.connect(self.remove_all_pages)
        self.menu._closeall.setEnabled(False)

        self.menu.addSpacer()

    def destroy(self):

        for menu_item in self.menu.widgets.values():
            menu_item.menuButtonClicked.clear()
            self.menu.removeMenuItem(menu_item)
        self.menu.widgets.clear()
        self.menu.close()
        #self.menu = None
        for page in self.pages.values():
            page.destroy()
        self.pages.clear()
        self.unread_pages.clear()
        self.recently_removed_pages.clear()

        self.screen.tab_bar.currentChanged.disconnect(self.on_switch_tab)
        self.currentChanged.disconnect(self.module.on_switch_page)

        self.layout().clear()
        self.close()
        #self.__dict__.clear()

    def connect_signals(self):

        self.screen.tab_bar.currentChanged.connect(self.on_switch_tab)
        self.currentChanged.connect(self.module.on_switch_page)

        self.on_switch_tab(0)

    @ttk.pyTTkSlot(int)
    def on_switch_tab(self, _tab_number):

        if self.screen.tab_bar.currentWidget() != self:
            return

        if self.header_bar is not None:
            self.screen.setWidget(widget=self.header_bar, position=self.screen.HEADER)

        self.module.on_switch_page(self.indexOf(self.currentWidget()))

    def on_remove_tab_changed(self, page):
        # self.switch_page_delay_timer = None
        self.remove_tab_changed(page_name)

    # Tab Highlights #

    def request_tab_changed(self, page, is_important=False, is_quiet=False):

        if self.module is not None:
            has_tab_changed = False
            is_current_tab = (self.screen.tab_bar.currentWidget() == self.module)
            is_current_page = (self.currentWidget() == page)

            if is_current_tab and is_current_page:
                return has_tab_changed

            if not is_quiet or is_important:
                # Highlight top-level tab, but don't for global feed unless mentioned
                #self.screen.tab_bar.request_tab_changed(self.parent_page, is_important)  ##
                has_tab_changed = self._append_unread_page(page.name(), is_important)
        else:
            has_tab_changed = True

        if has_tab_changed:
            self.update_page_tab_button(page.name())
            self.update_pages_menu_item(page.name())
            self.update_pages_count()

        return has_tab_changed

    def remove_tab_changed(self, page):

        self._remove_unread_page(page.name())

        # if has_tab_changed:
        self.update_page_tab_button(page.name())
        self.update_pages_menu_item(page.name())
        self.update_pages_count()

        # return True

    def _append_unread_page(self, page_name, is_important=False):

        # Remove existing page and move it to the end of the dict
        is_currently_important = self.unread_pages.pop(page_name, None)

        if is_currently_important and not is_important:
            # Important pages are persistent
            self.unread_pages[page_name] = is_currently_important
            return False

        self.unread_pages[page_name] = is_important

        if is_currently_important == is_important:
            return False

        return True

    def _remove_unread_page(self, page_name):

        if page_name not in self.unread_pages:
            return

        important_page_removed = self.unread_pages.pop(page_name)

        #if self.parent is None:
        #    return

        if not self.unread_pages:
            #self.window.notebook.remove_tab_changed(self.parent_page)
            return

        # No important unread pages left, reset top-level tab highlight
        if important_page_removed and not any(is_important for is_important in self.unread_pages.values()):
            pass
            #self.window.notebook.remove_tab_changed(self.parent_page)
            #self.window.notebook.request_tab_changed(self.parent_page, is_important=False)

    def _get_page_tab_color(self, page_name):

        if page_name in self.unread_pages:
            is_important = self.unread_pages[page_name]
            return TAB_COLORS["hilite"] if is_important else TAB_COLORS["changed"]

        return TAB_COLORS["default"]

    def update_pages_count(self):

        num_pages = len(self.unread_pages)

        if self.unread_pages:
            tooltip_text = ngettext("%s Unread Tab", "%s Unread Tabs", num_pages) % humanize(num_pages)
        else:
            tooltip_text = _("All Tabs")

        self.menu.setText(num_pages)
        self.menu.setToolTip(tooltip_text)

    def update_pages_menu_item(self, page_name):

        menu_item = self.menu.widgets.get(page_name, None)

        if page_name not in self.pages and menu_item is not None:
            self.menu.removeMenuItem(menu_item)
            del self.menu.widgets[page_name]
            self.menu._closeall.setEnabled(len(self.pages) > 0)
            return

        color = self._get_page_tab_color(page_name)

        if page_name in self.unread_pages:  # ✦
            text = ttk.TTkString(f"🟋 ", color + ttk.TTkColor.BLINKING) + ttk.TTkString(page_name, ttk.TTkColor.BOLD)
        else:
            text = ttk.TTkString(f"▪ ", color) + ttk.TTkString(page_name)  # application.room_list.get_room_icon_style()

        if menu_item is None:
            menu_item = self.menu.addMenu(text, data=page_name)
            menu_item.menuButtonClicked.connect(self.on_get_page)
            self.menu.widgets[page_name] = menu_item
            self.menu._closeall.setEnabled(True)

        menu_item.setText(text)

    def update_page_tab_button(self, page_name):

        color = self._get_page_tab_color(page_name)
        button = self.tabButton(self.indexOf(self.getWidgetByName(page_name)))
        button.setText(button.text().setColor(color, posFrom=2, posTo=len(button.text())))

    def restore_removed_page(self, *_args):

        if self.recently_removed_pages:
            self.on_restore_removed_page(page_args=self.recently_removed_pages.pop())

        if not self.recently_removed_pages:
            self.menu._reopen.setEnabled(False)

    def remove_page(self, page, page_args=None):

        self._remove_unread_page(page.name())

        if page_args:
            # Allow for restoring page after closing it
            self.recently_removed_pages.append(page_args)
            self.menu._reopen.setEnabled(True)

        #if self.parent_page is not None and self.get_n_pages() <= 0:
        #    if self.window.current_page_id == self.parent_page.id:
        #        self.window.notebook.grab_focus()

        #    self.parent.set_visible(False)

        del self.pages[page.name()]

        self.update_pages_menu_item(page.name())
        self.removeTab(self.indexOf(page))

        page.destroy()

    def on_restore_removed_page(self, page_args):
        raise NotImplementedError

    def on_remove_page(self):
        raise NotImplementedError

    def on_remove_all_pages(self, *_args):
        raise NotImplementedError

    def remove_all_pages(self, *_args):

        OptionDialog(
            parent=self.screen,
            title=_("Close All Tabs?"),
            message=_("Do you really want to close all tabs?"),
            buttons=[
                (OptionDialog.StandardButton.Cancel, _("_Cancel")),
                (OptionDialog.StandardButton.Yes, _("Close All"))
            ],
            default_button=OptionDialog.StandardButton.Cancel,
            destructive_button=OptionDialog.StandardButton.Yes,
            callback=self.on_remove_all_pages
        ).present()

    # Tab User Status #

    def set_user_status(self, user, status):

        button = self.tabButton(self.indexOf(self.getWidgetByName(user)))
        button.setText(USER_STATUS_ICONS.get(status) + ttk.TTkString(user, self._get_page_tab_color(user)))
        button.setToolTip(f"{user} ({USER_STATUS_LABELS.get(status)})")  # = page.name()

    def minimumHeight(self):
        return 0  # Keep main window status bar on top
