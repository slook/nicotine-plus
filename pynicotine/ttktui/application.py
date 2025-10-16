# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import threading
import time

from TermTk import TTkGridLayout
from TermTk.TTkCore import TTkTerm
from TermTk.TTkCore.constant import TTkK
from TermTk.TTkCore.shortcut import TTkShortcut
from TermTk.TTkCore.ttk import TTk

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.shares import PermissionLevel
from pynicotine.slskmessages import UserStatus


class Application:

    def __init__(self, ci_mode, isolated_mode):

        self._instance = TTk(
            title=pynicotine.__application_name__,
            layout=TTkGridLayout(),
            mouseTrack=True,
            # mouseCursor=True,
            sigmask=(TTkTerm.Sigmask.CTRL_C | TTkTerm.Sigmask.CTRL_Q | TTkTerm.Sigmask.CTRL_S | TTkTerm.Sigmask.CTRL_Z)
        )

        self.ci_mode = ci_mode
        self.isolated_mode = isolated_mode

        self.screen = None  # TTk.mainloop() will run in its own thread
        self.about = None
        self.fast_configure = None
        self.preferences = None
        self.plugin_settings = None
        self.chat_history = None
        self.room_list = None

        sys.excepthook = self.on_critical_error
        sys.unraisablehook = self._raise_exception

        for event_name, callback in (
            ("start", self.on_startup),
            ("confirm-quit", self.on_confirm_quit),
            ("invalid-password", self.on_invalid_password),
            ("invalid-username", self.on_invalid_username),
            # ("quit", self._instance.quit),  # TTkHelper.quit()
            ("server-login", self._update_user_status),
            ("server-disconnect", self._update_user_status),
            ("setup", self.on_fast_configure),
            ("shares-unavailable", self.on_shares_unavailable),
            # ("show-notification", self._show_notification),
            # ("show-chatroom-notification", self._show_chatroom_notification),
            # ("show-download-notification", self._show_download_notification),
            # ("show-private-chat-notification", self._show_private_chat_notification),
            # ("show-search-notification", self._show_search_notification),
            # ("show-upload-notification", self._show_upload_notification),
            ("user-status", self.on_user_status)
        ):
            events.connect(event_name, callback)

    def run(self):

        # TTk.mainloop() will run in its own thread
        from pynicotine.ttktui.mainscreen import MainScreen
        self.screen = MainScreen(self)  # Instantiate terminal drivers in main thread

        core.enabled_components.remove("cli")  # Don't start the core input processor
        core.start()

        # Main loop, process events from threads 10 times per second
        while events.process_thread_events():
            time.sleep(0.1)

        # Shut down with exit code 0 (success)
        self.on_shutdown()
        config.write_configuration()
        return 0

    # Primary Menus #

    def create_menus(self):

        self.file_menu = self.screen.header_menu.addMenu(_("_File"))  # .replace("_", "&"))
        self._create_file_menu(self.file_menu)

        self.shares_menu = self.screen.header_menu.addMenu(_("_Shares"))  #. replace("_", "&"))
        self._create_shares_menu(self.shares_menu)

        self.help_menu = self.screen.header_menu.addMenu(_("_Help"), alignment=TTkK.RIGHT_ALIGN)
        self._create_help_menu(self.help_menu)

        self.log_menu = self.screen.footer_menu.addMenu(" ∴ ")  # ⟃⟄ ⟥⟤ ⌕ ⎚ ⚉ ⁝ ∵ ∴ ⌤
        self.log_menu.setToolTip(_("_Log Categories"))
        self.create_log_menu(self.log_menu)

        self.view_menu = self.screen.tab_bar.addMenu("◨", position=TTkK.RIGHT)
        self._create_view_menu(self.view_menu)

    def destroy_menus(self):
        self.file_menu.close()
        self.shares_menu.close()
        self.help_menu.close()
        self.log_menu.close()
        self.view_menu.close()
        self.screen.header_menu.clear()
        # self.screen.header_menu.close()
        self.screen.footer_menu.clear()
        # self.screen.footer_menu.close()

    def _create_file_menu(self, menu_button):

        menu_button.server_connect = menu_button.addMenu(_("_Connect"))  # .replace("_", "&"))
        menu_button.server_connect.menuButtonClicked.connect(self.on_connect)
        menu_button.server_disconnect = menu_button.addMenu(_("_Disconnect"))  # .replace("_", "&"))
        menu_button.server_disconnect.menuButtonClicked.connect(self.on_disconnect)
        menu_button.server_privileges = menu_button.addMenu(_("Soulseek _Privileges"))  # .replace("_", "&"))

        self._update_user_status()

        menu_button.addSpacer()
        menu_button.addMenu(_("_Preferences")).menuButtonClicked.connect(self.on_preferences)
        menu_button.addSpacer()
        menu_button.quit = menu_button.addMenu(_("_Quit"))  # .replace("_", "&"))
        menu_button.quit.menuButtonClicked.connect(self.on_confirm_quit_request)

        self.sc_quit = TTkShortcut(
            TTkK.CTRL | TTkK.Key_Q, parent=self.screen, shortcutContext=TTkK.WidgetWithChildrenShortcut
        )
        self.sc_quit.activated.connect(self.on_confirm_quit_request)

    def _create_shares_menu(self, menu_button):

        menu_button.addMenu(_("_Rescan Shares")).menuButtonClicked.connect(self.on_rescan_shares)
        menu_button.addMenu(_("Configure _Shares")).menuButtonClicked.connect(self.on_configure_shares)
        menu_button.addSpacer()
        menu_button.addMenu(_("Browse _Public Shares")).menuButtonClicked.connect(self.on_browse_public_shares)
        menu_button.addMenu(_("Browse _Buddy Shares")).menuButtonClicked.connect(self.on_browse_buddy_shares)
        menu_button.addMenu(_("Browse _Trusted Shares")).menuButtonClicked.connect(self.on_browse_trusted_shares)

    def _create_help_menu(self, menu_button):

        menu_button.addMenu(_("_Keyboard Shortcuts")).menuButtonClicked.connect(self.on_keyboard_shortcuts)
        menu_button.addMenu(_("_Setup Assistant")).menuButtonClicked.connect(self.on_fast_configure)
        menu_button.addMenu(_("_Transfer Statistics")).menuButtonClicked.connect(self.on_transfer_statistics)
        if not self.isolated_mode:
            menu_button.addSpacer()
            menu_button.addMenu(_("Report a _Bug")).menuButtonClicked.connect(self.on_report_bug)
            menu_button.addMenu(_("Improve T_ranslations")).menuButtonClicked.connect(self.on_improve_translations)
        menu_button.addSpacer()
        menu_button.addMenu(_("_About Nicotine+")).menuButtonClicked.connect(self.on_about)

    def _create_view_menu(self, menu_button):

        menu_button._sidebar = menu_button.addMenu(
            "Buddies Sidebar", checkable=True, checked=(config.sections["ui"]["buddylistinchatrooms"] != "tab")
        )
        menu_button._sidebar.menuButtonClicked.connect(self.screen.buddies.set_buddy_list_position)

    def create_log_menu(self, menu_button):

        menu_button.download = menu_button.addMenu(_("Downloads"), data="download", checkable=True)
        menu_button.upload = menu_button.addMenu(_("Uploads"), data="upload", checkable=True)
        menu_button.search = menu_button.addMenu(_("Search"), data="search", checkable=True)
        menu_button.chat = menu_button.addMenu(_("Chat"), data="chat", checkable=True)
        menu_button.addSpacer()
        menu_button.connection = menu_button.addMenu(_("[Debug] [SLOW] Connections"), data="connection", checkable=True)
        menu_button.message = menu_button.addMenu(_("[Debug] [SLOW] Messages"), data="message", checkable=True)
        menu_button.transfer = menu_button.addMenu(_("[Debug] [SLOW] Transfers"), data="transfer", checkable=True)
        menu_button.miscellaneous = menu_button.addMenu(_("[Debug] [SLOW] Miscellaneous"),
                                                        data="miscellaneous", checkable=True)
        menu_button.addSpacer()
        menu_button.ttk_debug = menu_button.addMenu(_("[DEBUG] TTkLog"), data="DEBUG", checkable=True)
        menu_button.ttk_info = menu_button.addMenu(_("[INFO] TTkLog"), data="INFO", checkable=True)

        menu_button.menuButtonClicked.connect(self.screen.log_view.on_log_categories)

    def _update_user_status(self, *_args):

        is_online = (core.users.login_status != UserStatus.OFFLINE)

        for action in (self.file_menu.server_connect,):
            if action.isEnabled() != (not is_online):
                action.setEnabled(not is_online)

        # , "away-accel", "message-downloading-users", "message-buddies"):
        for action in (self.file_menu.server_disconnect, self.file_menu.server_privileges):
            if action.isEnabled() != is_online:
                action.setEnabled(is_online)

    # Core Events #

    def on_confirm_quit(self):

        from pynicotine.ttktui.widgets.dialogs import OptionDialog

        def response(dialog, button, _data):

            should_finish_uploads = dialog.get_option_value()

            if button == OptionDialog.StandardButton.Yes:
                if should_finish_uploads:
                    core.uploads.request_shutdown()
                else:
                    core.quit()

            elif button == OptionDialog.StandardButton.Save:
                from TermTk.TTkCore.drivers import TTkSignalDriver
                TTkSignalDriver.sigStop.emit()  # self.window.hide()

        if core.uploads.has_active_uploads():
            message = _("You are still uploading files. Do you really want to exit?")
            option_label = _("Wait for uploads to finish")
        else:
            message = _("Do you really want to exit?")
            option_label = None

        OptionDialog(
            parent=self.screen,
            icon=OptionDialog.Icon.Warning,
            title=_("Quit Nicotine+"),
            message=message,
            buttons=[
                (OptionDialog.StandardButton.No, _("_No")),
                (OptionDialog.StandardButton.Yes, _("_Quit")),
                (OptionDialog.StandardButton.Save, _("_Run in Background"))
            ],
            default_button=OptionDialog.StandardButton.No,
            destructive_button=OptionDialog.StandardButton.Yes,
            option_label=option_label,
            callback=response
        ).present()

    def on_shares_unavailable(self, shares):

        from pynicotine.ttktui.widgets.dialogs import OptionDialog

        def response(dialog, button, _data):
            dialog.close()
            core.shares.rescan_shares(force=(button == OptionDialog.StandardButton.Discard))

        shares_list_message = ""

        for virtual_name, folder_path in shares:
            shares_list_message += f'• "{virtual_name}" {folder_path}\n'

        dialog = OptionDialog(
            parent=self.screen,
            icon=OptionDialog.Icon.Warning,
            title=_("Shares Not Available"),
            message="Verify that external disks are mounted.",  # and folder permissions are correct."),
            long_message=shares_list_message,
            buttons=[
                (OptionDialog.StandardButton.Cancel, _("_Cancel")),
                (OptionDialog.StandardButton.Retry, _("_Retry")),
                (OptionDialog.StandardButton.Discard, _("_Force Rescan"))
            ],
            default_button=OptionDialog.StandardButton.Retry,
            callback=response
        )

        # Workaround dialog made invisible by other widgets updating on startup
        events.schedule(delay=0.1, callback=dialog.present)

    def on_invalid_password(self, *_args):
        self.on_fast_configure(invalid_password=True)

    def on_invalid_username(self, *_args):
        self.on_fast_configure(invalid_username=True)

    def on_user_status(self, msg):
        if msg.user == core.users.login_username:
            self._update_user_status()

    # Actions #

    def on_connect(self, *_args):
        if core.users.login_status == UserStatus.OFFLINE:
            core.connect()

    def on_disconnect(self, *_args):
        if core.users.login_status != UserStatus.OFFLINE:
            core.disconnect()

    def on_soulseek_privileges(self, *_args):
        pass  # core.users.request_check_privileges(should_open_url=True)

    def on_preferences(self, *_args, page_name="network"):

        if self.preferences is None:
            from pynicotine.ttktui.dialogs.preferences import Preferences
            self.preferences = Preferences(self)

        self.preferences.set_settings()
        self.preferences.set_active_page(page_name)
        self.preferences.present()

    def on_plugin_settings(self, *_args, plugin_name=None):

        if plugin_name is None:
            return

        metasettings = core.pluginhandler.get_plugin_metasettings(plugin_name)

        if not metasettings:
            return

        if self.plugin_settings is None:
            from pynicotine.ttktui.dialogs.pluginsettings import PluginSettings
            self.plugin_settings = PluginSettings(self)

        self.plugin_settings.load_options(plugin_name, metasettings)
        self.plugin_settings.present()

    def on_fast_configure(self, *_args, invalid_password=False, invalid_username=False):

        if self.fast_configure is None:
            from pynicotine.ttktui.dialogs.fastconfigure import FastConfigure
            self.fast_configure = FastConfigure(self)

        elif self.fast_configure.window is not None:
            self.fast_configure.close()

        change_account = invalid_password or invalid_username
        self.fast_configure.invalid_password = invalid_password
        self.fast_configure.invalid_username = invalid_username

        if change_account or config.need_config():
            # Workaround dialog made invisble by other widgets updating
            events.schedule(delay=0.2, callback=self.fast_configure.present)
            return

        self.fast_configure.present()

    def on_keyboard_shortcuts(self, *_args):
        pass  #

    def on_chat_history(self):
        self.chat_history.present()

    def on_room_list(self):
        self.room_list.present()

    def on_transfer_statistics(self, *_args):
        pass  #

    def on_report_bug(self, *_args):
        pass  #

    def on_improve_translations(self, *_args):
        pass  #

    def on_about(self, _button):

        if self.about is None:
            from pynicotine.ttktui.dialogs.about import About
            self.about = About(self)

        self.about.present()

    def on_rescan_shares(self, *_args):
        core.shares.rescan_shares()

    def on_configure_shares(self, *_args):
        self.on_preferences(page_name="shares")

    def on_configure_plugins(self, *_args):
        self.on_preferences(page_name="plugins")

    def on_browse_public_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.PUBLIC, new_request=True)

    def on_browse_buddy_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.BUDDY, new_request=True)

    def on_browse_trusted_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.TRUSTED, new_request=True)

    def on_away(self, *_args):
        """Away/Online status button."""

        if core.users.login_status == UserStatus.OFFLINE:
            core.connect()
            return

        core.users.set_away_mode(core.users.login_status != UserStatus.AWAY, save_state=True)

    # Running #

    def _raise_exception(self, exc_value):
        # Also show errors further down the stack in the core
        sys.excepthook = sys.__excepthook__
        # sys.unraisablehook = sys.__unraisablehook__
        # threading.excepthook = threading.__excepthook__
        raise exc_value

    def _on_critical_error(self, exc_type, exc_value, exc_traceback):

        if self.ci_mode:
            core.quit()
            self._raise_exception(exc_value)
            return

        from traceback import format_tb

        # Check if exception occurred in a plugin
        if exc_traceback is not None:
            traceback = exc_traceback

            while traceback.tb_next:
                file_path = traceback.tb_frame.f_code.co_filename

                for plugin_name in core.pluginhandler.enabled_plugins:
                    plugin_path = core.pluginhandler.get_plugin_path(plugin_name)

                    if file_path.startswith(plugin_path):
                        core.pluginhandler.show_plugin_error(plugin_name, exc_value)
                        return

                traceback = traceback.tb_next

        from TermTk import __version__ as TTk_version

        # Show critical error dialog
        # loop = GLib.MainLoop()
        error = (f"Nicotine+ Version: {pynicotine.__version__}\nTTk Version: {TTk_version}\n"
                 f"Python Version: {sys.version.split()[0]} ({sys.platform})\n\n"
                 f"Type: {exc_type}\nValue: {exc_value}\nTraceback:\n{''.join(format_tb(exc_traceback))}")
        # self._show_critical_error_dialog(error, loop)
        log.add(error)
        # print(error)

        # Keep dialog open if error occurs on startup
        # loop.run()

        # Dialog was closed, quit
        core.quit()
        events.emit("quit")

        # Process 'quit' event after slight delay in case thread event loop is stuck
        # GLib.idle_add(lambda: events.process_thread_events() == -1, priority=GLib.PRIORITY_HIGH_IDLE)
        # if self.screen is not None:
        #     self.screen.join(timeout=1)

        events.process_thread_events()

        # Log exception in terminal
        self._raise_exception(exc_value)

    def on_critical_error(self, exc_type, exc_value, exc_traceback, *_args):

        if threading.current_thread() is threading.main_thread():
            self._on_critical_error(exc_type, exc_value, exc_traceback)
            return

        # Raise exception in the main thread
        events.invoke_main_thread(self._on_critical_error, exc_type, exc_value, exc_traceback)

    def on_confirm_quit_request(self, *_args):

        if not config.sections["ui"]["exitdialog"]:
            core.quit()
        else:
            core.confirm_quit()

    # def on_force_quit_request(self, *_args):
    #     core.quit()

    def on_quit_request(self, *_args):

        if not core.uploads.has_active_uploads():
            core.quit()
            return

        core.confirm_quit()

    def on_startup(self):

        from pynicotine.ttktui.dialogs.chathistory import ChatHistory
        from pynicotine.ttktui.dialogs.roomlist import RoomList
        from TermTk import __version__ as TTk_version

        self.chat_history = ChatHistory(self)
        self.room_list = RoomList(self)

        log.add(_("Loaded %(program)s %(version)s"), {"program": "TTk", "version": TTk_version})

        # if self.screen is None:
        #     # TTk.mainloop() will run in the plugin system thread
        #     from pynicotine.ttktui.mainscreen import MainScreen
        #     self.screen = MainScreen(self)
        #     self.screen.present()  # Run TTk.mainloop()
        #     self.on_shutdown()
        #     return

        self.screen.start()  # Start a new Thread for running TTk.mainloop()

        if config.sections["server"]["auto_connect_startup"]:
            core.connect()

    def on_shutdown(self, *_args):

        # from pynicotine.cli import cli

        # for event_name, callback in (
        #     ("cli-prompt-finished", cli._cli_prompt_finished),
        #     ("log-message", cli._log_message)
        # ):
        #     events.connect(event_name, callback)

        # core.enabled_components.add("cli")
        # cli.enable_logging()

        if self.about is not None:
            self.about.destroy()

        if self.fast_configure is not None:
            self.fast_configure.destroy()

        if self.preferences is not None:
            self.preferences.destroy()

        if self.plugin_settings is not None:
            self.plugin_settings.destroy()

        if self.chat_history is not None:
            self.chat_history.destroy()

        if self.room_list is not None:
            self.room_list.destroy()

        if self.screen is not None:
            self.screen.destroy()

        self.__dict__.clear()
