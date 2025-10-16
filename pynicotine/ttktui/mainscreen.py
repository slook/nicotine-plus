# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2016-2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2009 hedonist <ak@sensi.org>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-FileCopyrightText: 2003-2004 Nicotine Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
# import sys
import time

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.buddies import Buddies
from pynicotine.ttktui.chatrooms import ChatRooms
from pynicotine.ttktui.downloads import Downloads
from pynicotine.ttktui.interests import Interests
from pynicotine.ttktui.privatechat import PrivateChats
from pynicotine.ttktui.uploads import Uploads
from pynicotine.ttktui.userbrowse import UserBrowses
from pynicotine.ttktui.userinfo import UserInfos
from pynicotine.ttktui.search import Searches
from pynicotine.ttktui.widgets.console import Console
from pynicotine.ttktui.widgets.screen import Screen
from pynicotine.ttktui.widgets.statusbar import StatusBar
from pynicotine.ttktui.widgets.tabs import Tabs
from pynicotine.ttktui.widgets.theme import USER_STATUS_COLORS
from pynicotine.slskmessages import UserStatus


class MainScreen(Screen):

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

    def __init__(self, application):
        super().__init__(application)

        self.application = application

        self.auto_away = False
        self.away_timer_id = None
        self.away_cooldown_time = 0

        # Layout
        self.header_bar = None
        self.header_menu = None
        self.tab_bar = None
        self.side_bar = None
        self.log_view = None
        self.footer_menu = None
        self.status_bar = None

        # Secondary tab bars
        self.interests = Interests(self)
        self.chatrooms = ChatRooms(self)
        self.search = Searches(self)
        self.downloads = Downloads(self)
        self.uploads = Uploads(self)
        self.buddies = Buddies(self)
        self.privatechat = PrivateChats(self)
        self.userinfo = UserInfos(self)
        self.userbrowse = UserBrowses(self)

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
        # core.enabled_components.remove("cli")
        from pynicotine.cli import cli
        cli._quit()  # Restore normal stdout settings

        for event_name, callback in (
            ("cli-prompt-finished", cli._cli_prompt_finished),
            ("log-message", cli._log_message)
        ):
            if callback in events._callbacks[event_name]:
                events.disconnect(event_name, callback)

        for event_name, callback in (
            ("log-message", self.log_callback),
            ("quit", self.on_quit),
            ("server-login", self.update_user_status),
            ("server-disconnect", self.update_user_status),
            ("set-connection-stats", self.set_connection_stats),
            # ("shares-preparing", self.shares_preparing),
            # ("shares-ready", self.shares_ready),
            # ("shares-scanning", self.shares_scanning),
            ("start", self.init_screen),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    # Initialize #

    def init_screen(self):

        # Apply UI customizations (ASCII, UTF8, NERD)
        ttk.TTkTheme.loadTheme(ttk.TTkTheme.UTF8)

        # HEADER
        self.header_bar = ttk.TTkContainer(minHeight=1)
        self.header_bar.setLayout(ttk.TTkHBoxLayout())
        self.header_menu = ttk.TTkMenuBarLayout()

        # MAIN
        self.tab_bar = Tabs(self)  # , alignment=ttk.TTkK.CENTER_ALIGN)

        # RIGHT
        self.side_bar = ttk.TTkContainer(visible=config.sections["ui"]["buddylistinchatrooms"] != "tab")

        # BOTTOM
        self.log_view = LogView(self, visible=not config.sections["logging"]["logcollapsed"])

        # FOOTER
        self.footer_menu = ttk.TTkMenuBarLayout()
        self.status_bar = StatusBar(self)

        # Actions and menu
        self.application.create_menus()

        self.setMenuBar(self.header_menu, position=self.HEADER)
        self.setMenuBar(self.footer_menu if self.log_view.isVisible() else None, position=self.FOOTER)

        # Layout
        self.setWidget(widget=self.header_bar, position=self.HEADER, fixed=True)
        self.setWidget(widget=self.tab_bar, position=self.MAIN)
        self.setWidget(widget=self.log_view, position=self.BOTTOM, border=True, size=12)
        self.setWidget(widget=self.status_bar, position=self.FOOTER, fixed=True)
        self.setWidget(widget=self.side_bar, position=self.RIGHT)

        # Tab visibility/order
        self.append_main_tabs()
        # self.set_tab_positions()
        # self.set_main_tabs_order()
        self.set_main_tabs_visibility()
        self.connect_tab_signals()
        self.set_last_session_tab()

    # Main Tab Bar #

    def show_tab(self, tab_number, tab_widget, tab_name):

        if self.tab_bar.getWidgetByName(tab_name) is None:
            tab_text = self.TAB_LABELS.get(tab_name)
            _tab_index = self.tab_bar.insertTab(tab_number, tab_widget, f"  {tab_text}  ", data="")
            self.tab_bar.update_tab_button(self.tab_bar.getWidgetByName(tab_name))

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

        for tab_number, tab_name in enumerate(config.sections["ui"]["modes_order"]):
            if not config.sections["ui"]["modes_visible"].get(tab_name, True):
                continue

            tab_widget = self.tabs[tab_name]

            if tab_name == "userlist" and config.sections["ui"]["buddylistinchatrooms"] != "tab":
                continue

            tab_index = self.show_tab(tab_number, tab_widget, tab_name)

        if tab_index is None:
            self.show_tab(0, self.search, "search")

    def connect_tab_signals(self):

        self.chatrooms.connect_signals()
        self.search.connect_signals()
        self.privatechat.connect_signals()
        self.userinfo.connect_signals()
        self.userbrowse.connect_signals()

        self.buddies.create_header()
        self.downloads.create_header()
        self.uploads.create_header()
        self.interests.create_header()

        self.tab_bar.connect_signals()
        self.status_bar.connect_signals()

    def set_last_session_tab(self):

        tab = None

        if config.sections["ui"]["tab_select_previous"]:
            tab = self.tab_bar.getWidgetByName(config.sections["ui"]["last_tab_id"])

        if tab is None:
            # Default tab at position index 0
            tab = self.tab_bar.currentWidget()

        if tab == self.tab_bar.currentWidget():
            self.tab_bar.currentChanged.emit(self.tab_bar.currentIndex())
            return

        self.tab_bar.setCurrentWidget(tab)

    # Headerbar/Toolbar #

    def minimumWidth(self):
        return 0  # Allow shrinking of centered header bar

    def set_active_header_bar(self, tab):
        """Switch out the active headerbar for another one.

        This is used when changing the active notebook tab.
        """

        # if config.sections["ui"]["header_bar"]:
        # self.hide_current_header_bar()
        # self.show_header_bar(tab_name)
        self.setWidget(widget=tab.header_bar, position=self.HEADER)

        config.sections["ui"]["last_tab_id"] = tab.name()

        self.on_cancel_auto_away()

    def set_main_tabs_visibility(self):
        # self.buddies.set_buddy_list_position(self.buddies_sidebar_check)
        # self.application.view_menu._sidebar.setChecked(config.sections["ui"]["buddylistinchatrooms"] != "tab")
        pass

    def focus_default_widget(self):

        if not ttk.TTkHelper.checkModalOverlay(self):
            return

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
        self.status_bar.user_status_button.update_status(status, username)

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
            self.status_bar.user_status_button.setEnabled(False)
            # self.status_bar.user_status_button.clearFocus()

        if core.uploads.pending_shutdown:
            core.uploads.cancel_shutdown()
        else:
            self.application.on_away()

    def set_status_text(self, text):
        self.status_bar.setText(text)

    def set_connection_stats(self, total_conns=0, download_bandwidth=0, upload_bandwidth=0, **_kwargs):
        self.status_bar.set_connection_stats(total_conns, download_bandwidth, upload_bandwidth)

    # Log Pane #

    def log_callback(self, timestamp_format, msg, title, level):
        events.invoke_main_thread(self.update_log, timestamp_format, msg, title, level)

    def update_log(self, timestamp_format, msg, title, level):

        # if title:
        #     MessageDialog(parent=self, title=title, message=msg, selectable=True).present()

        # Keep verbose debug messages out of statusbar to make it more useful
        if level not in {"transfer", "connection", "message", "miscellaneous"}:
            self.set_status_text(msg)

        self.log_view.log_callback_app(timestamp_format, msg, title, level)

    def on_quit(self, *_args):
        self.remove_away_timer()

    def destroy(self):

        ttk.TTkHelper.quit()
        # time.sleep(0.01)
        super().destroy()
        # ttk.pyTTkSignal.clearAll()
        # time.sleep(0.01)

        self.tab_bar.destroy()  # disconnect indexChanged slot

        for tab in self.tabs.values():
            tab.destroy()
            self.tab_bar.removeTab(self.tab_bar.indexOf(tab))

        # self.tab_bar.close()
        self.side_bar.close()
        self.log_view.hide()
        self.log_view.close()

        time.sleep(0.1)
        self.status_bar.destroy()
        self.application.destroy_menus()
        self.setMenuBar(None, position=self.HEADER)
        self.setMenuBar(None, position=self.FOOTER)
        # self.layout().clear()
        # self.close()

        ttk.pyTTkSignal.clearAll()


class LogView(Console):

    def __init__(self, screen, **kwargs):
        super().__init__(**kwargs)

        self.screen = screen

        ttk.TTkLog.installMessageHandler(self.log_callback_ttk)
        self.ttk_enabled_modes = ["CRITICAL", "FATAL"]

        if "miscellaneous" in config.sections["logging"]["debugmodes"]:
            self.ttk_enabled_modes.extend(["WARNING", "ERROR", "DEBUG", "INFO"])

    @ttk.pyTTkSlot(int, int)
    def on_resize(self, _w, h):
        if h <= self.minimumHeight():
            self.hide_log()
            self.screen.setWidget(widget=self, position=self.screen.BOTTOM, border=True, size=12)

    def hide_log(self):

        config.sections["logging"]["logcollapsed"] = True
        self.setVisible(False)

        self.screen.setMenuBar(None, position=self.screen.FOOTER)
        self.screen.focus_default_widget()

        self.enlarge_button.menuButtonClicked.disconnect(self.on_enlarge_log_pane)
        self.sizeChanged.disconnect(self.on_resize)

    def show_log(self):

        config.sections["logging"]["logcollapsed"] = False
        self.setVisible(True)

        self.screen.setMenuBar(self.screen.footer_menu, position=self.screen.FOOTER)
        self.console_area.console_view.scroll_bottom(force=True)

        self.setFocus()

        self.enlarge_button.menuButtonClicked.connect(self.on_enlarge_log_pane)
        self.sizeChanged.connect(self.on_resize)

    # @ttk.pyTTkSlot(ttk.TTkMenuButton)
    # def on_hide_log_pane(self, _button):
    #     self.hide_log()

    # @ttk.pyTTkSlot(ttk.TTkMenuButton)
    # def on_show_log_pane(self, _button):
    #     self.show_log()

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_enlarge_log_pane(self, button):

        if button.isChecked():
            button.setText("⏏")
            button.setChecked(False)
            new_height = button.data()
        else:
            button.setData(self.height())
            button.setText("▂")
            button.setChecked(True)
            new_height = self.screen.height()

        self.screen.setWidget(widget=self, position=self.screen.BOTTOM, border=True, size=new_height)

        if new_height > button.data():
            # self.search_bar.on_find_start()
            self.console_area.console_view.viewMoveTo(0, 0)
        else:
            # self.search_bar.on_find_end()
            self.console_area.console_view.scroll_bottom(force=True)

        self.setFocus()

    def setFocus(self):
        if not super().setFocus():
            self.screen.focus_default_widget()

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_log_categories(self, menu_button):

        for toggle_button in (
            menu_button.download,
            menu_button.upload,
            menu_button.search,
            menu_button.chat,
            menu_button.connection,
            menu_button.message,
            menu_button.transfer,
            menu_button.miscellaneous
        ):
            toggle_button.setChecked(toggle_button.data() in config.sections["logging"]["debugmodes"])
            toggle_button.menuButtonClicked.connect(self.on_log_category)

        for toggle_button in (
            menu_button.ttk_info,
            menu_button.ttk_debug,
        ):
            toggle_button.setChecked(toggle_button.data() in self.ttk_enabled_modes)
            toggle_button.menuButtonClicked.connect(self.on_log_ttk)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_log_category(self, toggle_button):

        from pynicotine.logfacility import log

        if toggle_button.isChecked():
            log.add_log_level(toggle_button.data())
        else:
            log.remove_log_level(toggle_button.data())

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_log_ttk(self, toggle_button):

        if toggle_button.isChecked():
            if toggle_button.data() not in self.ttk_enabled_modes:
                self.ttk_enabled_modes.append(toggle_button.data())

        elif toggle_button.data() in self.ttk_enabled_modes:
            self.ttk_enabled_modes.remove(toggle_button.data())

        if not self.ttk_enabled_modes:
            ttk.TTkLog._messageHandler.clear()

        elif not ttk.TTkLog._messageHandler:
            ttk.TTkLog.installMessageHandler(self.log_callback_ttk)

    def log_callback_ttk(self, mode, context, message):

        logType = self.TTK_LOG_MODES.get(mode, "NONE")

        if str(logType) not in self.ttk_enabled_modes:
            return

        ctx = ttk.TTkString(
            f" {context.file.rpartition(os.sep)[-1]}:{context.line} {context.function}(): ", ttk.TTkColor.GREEN
        )
        self.add_line(ttk.TTkString("[") + logType + ttk.TTkString("]") + ctx + ttk.TTkString(message), level=mode)

    def log_callback_app(self, timestamp_format, msg, _title, level):

        if timestamp_format:
            # The console renders the timestamp strings from raw data on demand
            self.console_area.console_view.timestamp_format = timestamp_format

        self.add_line(msg, level)
