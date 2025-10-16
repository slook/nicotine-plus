# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2016-2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2009 hedonist <ak@sensi.org>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys
import textwrap
import time

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.buddies import Buddies
from pynicotine.ttktui.chatrooms import ChatRooms
from pynicotine.ttktui.privatechat import PrivateChats
from pynicotine.ttktui.userinfo import UserInfos
from pynicotine.ttktui.widgets.screen import Screen
from pynicotine.ttktui.widgets.theme import USER_STATUS_COLORS
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS
from pynicotine.slskmessages import UserStatus


TAB_LABELS = {
    "search": _("Search Files"),
    "downloads": _("Downloads"),
    "uploads": _("Uploads"),
    "userbrowse": _("Browse Shares"),
    "userinfo": _("User Profiles"),
    "private": _("Private Chat"),
    "userlist": _("Buddies"),
    "chatrooms": _("Chat Rooms"),
    "interests": _("Interests")
}


class MainScreen(Screen):

    def __init__(self, application):
        super().__init__(application)

        self.application = application
        self.auto_away = False
        self.away_timer_id = None
        self.away_cooldown_time = 0

        # Header Bar
        self.header_bar = ttk.TTkContainer(minHeight=1)
        self.header_bar.setLayout(ttk.TTkHBoxLayout())
        self.header_menu = ttk.TTkMenuBarLayout()

        # Main Center
        self.tab_bar = ttk.TTkTabWidget(border=False, closable=False)  # , alignment=ttk.TTkK.CENTER_ALIGN)

        # Right
        self.side_bar = ttk.TTkContainer(visible=(config.sections["ui"]["buddylistinchatrooms"] != "tab"))

        # Bottom
        self.log_view = ttk.TTkLogViewer()
        self.footer_menu = ttk.TTkMenuBarLayout()

        # Status Bar
        self.status_bar = ttk.TTkContainer(minHeight=1, layout=ttk.TTkHBoxLayout())
        self.status_label_container = ttk.TTkContainer(parent=self.status_bar, paddingLeft=1)
        self.status_label = ttk.TTkLabel(parent=self.status_label_container, text="Starting…")
        self.status_ellipsis = ttk.TTkLabel(parent=self.status_bar, text="…", minWidth=2, maxWidth=2, visible=False)

        #         ⯅⯆   ▼▲  ▽△   ▾▴  ▿▵  ⏬⏫  ⏷⏶  ⏬⏫   ∇∆  🠉🠋     🠛🠝    🠯🠭    🠹🠻    🡃🡁    🡇🡅    🡳🡱    🢃🢁    🢇🢅    🢗🢕    ⮉⮋    ⮝⮟    🞃🞁
        _spacer1 = ttk.TTkSpacer(parent=self.status_bar, minWidth=2, maxWidth=4)

        self.download_status_button = ttk.TTkLabel(
            parent=self.status_bar, minWidth=16, maxWidth=16, alignment=ttk.TTkK.RIGHT_ALIGN,
            text=ttk.TTkString("▼ 0 Kb/s", ttk.TTkColor.fg("#AAAAAA")).setColorAt(0, ttk.TTkColor.GREEN)
        )  #           ⇩⇓ ↧↡↓⇣⇟ 🮦🭭🮧🭯🮚
        self.download_status_button.setToolTip("Downloading Speed")

        self.upload_status_button = ttk.TTkLabel(
            parent=self.status_bar, minWidth=16, maxWidth=16, alignment=ttk.TTkK.RIGHT_ALIGN,
            text=ttk.TTkString("▲ 0 Kb/s", ttk.TTkColor.fg("#AAAAAA")).setColorAt(0, ttk.TTkColor.CYAN)
        )  #        ⇬⇯⇮⇧⇑⇪↥↟↑⇡⇞ 🮧🭯🮦🭭🮚   🭭🮷🮵🮶🮸 🭯   🮦🭮🮵🮶🭬🮧
        self.upload_status_button.setToolTip("Uploading Speed")

        _spacer2 = ttk.TTkSpacer(parent=self.status_bar, minWidth=2, maxWidth=4)

        self.user_status_button = ttk.TTkButton(
            parent=self.status_bar, checkable=False, minWidth=14, maxWidth=14,
            text=ttk.TTkString(USER_STATUS_LABELS[UserStatus.OFFLINE].upper(), ttk.TTkColor.BOLD), addStyle={
                'default': {
                    'color': ttk.TTkColor.WHITE + USER_STATUS_COLORS[UserStatus.OFFLINE].invertFgBg(),
                    'borderColor': ttk.TTkColor.BG_RED + ttk.TTkColor.BLINKING,
                },
                'disabled': {
                    'color': ttk.TTkColor.bg("#888888") + ttk.TTkColor.BLINKING,
                    'borderColor': ttk.TTkColor.fg("#888888"),
                },
                'hover': {
                    'color': ttk.TTkColor.YELLOW + ttk.TTkColor.BG_RED,
                    'borderColor': ttk.TTkColor.RST + ttk.TTkColor.fg("#FFFFCC") + ttk.TTkColor.BLINKING,
                },
                'checked': {
                    'color': ttk.TTkColor.BLACK + USER_STATUS_COLORS[UserStatus.AWAY].invertFgBg(),
                    'borderColor': ttk.TTkColor.BG_YELLOW,
                },
                'unchecked': {
                    'color': ttk.TTkColor.BLACK + USER_STATUS_COLORS[UserStatus.ONLINE].invertFgBg(),
                    'borderColor': ttk.TTkColor.BG_GREEN,
                },
                'clicked': {
                    'color': ttk.TTkColor.fg("#FFFFDD"),
                    'borderColor': ttk.TTkColor.fg("#DDDDDD") + ttk.TTkColor.BOLD,
                },
                'focus': {
                    'color': ttk.TTkColor.fgbg("#dddd88", "#0000AA"),
                    'borderColor': ttk.TTkColor.RST + ttk.TTkColor.fg("#ffff00") + ttk.TTkColor.BLINKING,
                },
            }
        )
        #self.user_status_button.setFocusPolicy(ttk.TTkK.FocusPolicy.StrongFocus)
        self.user_status_button.clicked.connect(self.on_toggle_status)
        self.status_label_container.sizeChanged.connect(self.on_resize_status_bar)

        # Secondary tab bars
        self.interests = ttk.TTkFrame(title=_("Interests"), name="interests")  # Interests(self)
        self.chatrooms = ChatRooms(self)
        self.search = ttk.TTkTabWidget(border=False, closable=True, name="search")  # Searches(self)
        self.downloads = ttk.TTkTree(name="downloads")  # Downloads(self)
        self.uploads = ttk.TTkTree(name="uploads")  # Uploads(self)
        self.buddies = Buddies(self)
        self.privatechat = PrivateChats(self)
        self.userinfo = UserInfos(self)
        self.userbrowse = ttk.TTkTabWidget(border=False, closable=True, name="userbrowse")  # UserBrowses(self)

        # Main tab bar
        self.tabs = {
            "chatrooms": self.chatrooms,
            "downloads": self.downloads,
            "interests": self.interests,
            "private": self.privatechat,
            "search": self.search,
            "uploads": self.uploads,
            "userbrowse": self.userbrowse,
            "userinfo": self.userinfo,
            "userlist": self.buddies
        }

        # Core events
        for event_name, callback in (
            ("log-message", self.log_callback),
            #("quit", self.on_quit),
            ("server-login", self.update_user_status),
            ("server-disconnect", self.update_user_status),
            #("set-connection-stats", self.set_connection_stats),
            #("shares-preparing", self.shares_preparing),
            #("shares-ready", self.shares_ready),
            #("shares-scanning", self.shares_scanning),
            #("start", self.init_screen),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    # Initialize #

    def load(self):

        # Apply UI customizations (ASCII, UTF8, NERD)
        ttk.TTkTheme.loadTheme(ttk.TTkTheme.UTF8)

        # Actions and menu
        self.create_menus()

        # Layout
        self.setWidget(widget=self.header_bar, position=self.HEADER, fixed=True)
        self.setWidget(widget=self.tab_bar, position=self.MAIN)
        self.setWidget(widget=self.status_bar, position=self.FOOTER, fixed=True)

        self.on_show_log_pane(not config.sections["logging"]["logcollapsed"])

        self.setWidget(widget=self.side_bar, position=self.RIGHT)
        #self.setWidget(widget=self.log_view, position=self.BOTTOM, size=4)

        # Tab visibility/order
        self.append_main_tabs()
        #self.set_tab_positions()
        #self.set_main_tabs_order()
        self.set_main_tabs_visibility()
        self.connect_tab_signals()
        self.set_last_session_tab()

    # Primary Menus #

    def create_menus(self):

        self.application.create_file_menu(self.header_menu)
        self.application.create_shares_menu(self.header_menu)
        self.application.create_help_menu(self.header_menu, position=ttk.TTkK.RIGHT_ALIGN)
        self.application.create_log_menu(self.footer_menu, position=ttk.TTkK.CENTER_ALIGN)

        self.setMenuBar(self.header_menu, position=self.HEADER)
        self.setMenuBar(self.footer_menu, position=self.FOOTER)

        self.application.create_view_menu(self.tab_bar, position=ttk.TTkK.RIGHT)

    # Main Tab Bar #

    def show_tab(self, tab_number, tab_widget, tab_name):

        if self.tab_bar.getWidgetByName(tab_name) is None:
            tab_text = TAB_LABELS.get(tab_name)
            tab_index = self.tab_bar.insertTab(tab_number, tab_widget, f"  {tab_text}  ", data=tab_name)

        config.sections["ui"]["modes_visible"][tab_name] = True

        return self.tab_bar.indexOf(tab_widget)

    def hide_tab(self, tab_name):

        tab_widget = self.tab_bar.getWidgetByName(tab_name)
        tab_index = self.tab_bar.indexOf(tab_widget)

        if self.tab_bar.widget(tab_index) is None:  # = self.tabs.get(tab_name):
            return

        self.tab_bar.removeWidget(tab_widget)
        self.tab_bar.removeTab(tab_index)

        config.sections["ui"]["modes_visible"][tab_name] = False

    def append_main_tabs(self):

        tab_index = None

        for tab_number, tab_name in enumerate(config.sections["ui"]["modes_order"], start=1):
            if not config.sections["ui"]["modes_visible"].get(tab_name, True):
                continue

            tab_widget = self.tabs[tab_name]

            if tab_name == "userlist" and config.sections["ui"]["buddylistinchatrooms"] != "tab":
                continue

            tab_index = self.show_tab(tab_number, tab_widget, tab_name)

        if tab_index is None:
            self.show_tab(1, self.tabs["search"], "search")

    def connect_tab_signals(self):

        self.tab_bar.currentChanged.connect(self.on_switch_tab)

        self.chatrooms.connect_signals()
        # self.search.connect_signals()
        self.privatechat.connect_signals()
        self.userinfo.connect_signals()
        # self.userbrowse.connect_signals()
        self.buddies.connect_signals()

    @ttk.pyTTkSlot(int)
    def on_switch_tab(self, tab_index):

        self.set_active_header_bar(self.tab_bar.widget(tab_index).name())

        self.on_cancel_auto_away()

    def set_main_tabs_visibility(self):
        #self.buddies.set_buddy_list_position(self.buddies_sidebar_check)
        self.application.view_menu._sidebar.setChecked(config.sections["ui"]["buddylistinchatrooms"] != "tab")

    def set_last_session_tab(self):

        if not config.sections["ui"]["tab_select_previous"]:
            return

        tab = self.tab_bar.getWidgetByName(config.sections["ui"]["last_tab_id"])

        if tab is None:  # or not tab.isVisible():
            return

        self.tab_bar.setCurrentWidget(tab)

    # Headerbar/Toolbar #

    def set_active_header_bar(self, tab_name):
        """Switch out the active headerbar for another one.

        This is used when changing the active notebook tab.
        """

        #if config.sections["ui"]["header_bar"]:
        #self.hide_current_header_bar()
        #self.show_header_bar(tab_name)

        config.sections["ui"]["last_tab_id"] = tab_name

    def focus_default_widget(self):

        tab = self.tab_bar.currentWidget()

        if not hasattr(tab, "focus_default_widget"):
            # Tab doesn't have default focus, fall back to the top tab bar
            self.tab_bar.setFocus()
            return

        tab.focus_default_widget()

    # Connection #

    def update_user_status(self, *_args):

        status = core.users.login_status
        is_away = (status == UserStatus.AWAY)

        # Away mode
        if not is_away:
            self.set_auto_away(False)
        else:
            self.remove_away_timer()

        # Status button
        username = core.users.login_username
        status_icon = USER_STATUS_ICONS.get(status)
        status_text = USER_STATUS_LABELS.get(status).upper()

        if username is not None:
            self.user_status_button.setCheckable(True)
            self.user_status_button.setChecked(is_away)
            self.user_status_button.setToolTip(status_icon + ttk.TTkString(username))

        elif self.user_status_button.isCheckable():
            self.user_status_button.setCheckable(False)
            self.user_status_button.setToolTip("")

        if str(self.user_status_button.text()) != status_text:
            self.user_status_button.setText(ttk.TTkString(status_text, ttk.TTkColor.BOLD))

        if not self.user_status_button.isEnabled():
            self.user_status_button.setEnabled(True)

            if status != UserStatus.OFFLINE:
                # Don't disrupt invalid password dialog
                self.focus_default_widget()

    def user_status(self, msg):
        if msg.user == core.users.login_username:
            self.update_user_status()

    # Away Mode #

    def set_auto_away(self, active=True):

        if active:
            self.auto_away = True
            self.away_timer_id = None

            if core.users.login_status != UserStatus.AWAY:
                core.users.set_away_mode(True)

            return

        if self.auto_away:
            self.auto_away = False

            if core.users.login_status == UserStatus.AWAY:
                core.users.set_away_mode(False)

        # Reset away timer
        self.remove_away_timer()
        self.create_away_timer()

    def create_away_timer(self):

        if core.users.login_status != UserStatus.ONLINE:
            return

        away_interval = config.sections["server"]["autoaway"]

        if away_interval > 0:
            self.away_timer_id = events.schedule(delay=(60 * away_interval), callback=self.set_auto_away)

    def remove_away_timer(self):
        events.cancel_scheduled(self.away_timer_id)

    def on_cancel_auto_away(self, *_args):

        current_time = time.monotonic()

        if (current_time - self.away_cooldown_time) >= 5:
            self.set_auto_away(False)
            self.away_cooldown_time = current_time

    # Status Bar #

    @ttk.pyTTkSlot()
    def on_toggle_status(self):

        if core.users.login_status != UserStatus.OFFLINE:
            self.user_status_button.setEnabled(False)
            self.user_status_button.clearFocus()

        if core.uploads.pending_shutdown:
            core.uploads.cancel_shutdown()
        else:
            self.application.on_away()

    @ttk.pyTTkSlot(int, int)
    def on_resize_status_bar(self, _w, _h):
        self.set_status_text(str(self.status_label.text()))

    def set_status_text(self, text):

        self.status_label.setText(text)

        if self.status_label.minimumWidth() >= self.status_label_container.width():
            self.status_label.setToolTip(textwrap.fill(text, width=self.status_bar.width(), replace_whitespace=False))
            self.status_ellipsis.setVisible(True)
        else:
            self.status_label.setToolTip("")
            self.status_ellipsis.setVisible(False)

    # Log Pane #

    def log_callback(self, timestamp_format, msg, title, level):
        events.invoke_main_thread(self.update_log, timestamp_format, msg, title, level)

    def update_log(self, timestamp_format, msg, title, level):

        #if title:
        #    MessageDialog(parent=self, title=title, message=msg, selectable=True).present()

        # Keep verbose debug messages out of statusbar to make it more useful
        if level not in {"transfer", "connection", "message", "miscellaneous"}:
            self.set_status_text(msg)

        #if not config.sections["logging"]["logcollapsed"]:
            #self.log_view.add_line(msg, timestamp_format=timestamp_format)
        ttk.TTkLog.info(msg)

    @ttk.pyTTkSlot(bool)
    def on_show_log_pane(self, visible):

        if visible:
            self.setWidget(widget=self.log_view, position=self.BOTTOM, border=True, size=4)
        else:
            self.setWidget(widget=self.log_view, position=self.BOTTOM, border=False, size=0)

        config.sections["logging"]["logcollapsed"] = not visible

    def destroy(self):

        self.status_label_container.sizeChanged.disconnect(self.on_resize_status_bar)
        self.user_status_button.clicked.disconnect(self.on_toggle_status)

        for tab in self.tabs.values():
            if hasattr(tab, "destroy"):
                tab.destroy()
            tab.close()

        if self.log_view is not None:
            self.log_view.close()

        ttk.TTkHelper.quit()

        super().destroy()
