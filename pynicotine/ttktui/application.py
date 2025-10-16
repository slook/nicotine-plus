# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import sys
import threading
import time

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.shares import PermissionLevel
from pynicotine.slskmessages import UserStatus

from TermTk import TTkGridLayout
from TermTk.TTkCore import TTkTerm
from TermTk.TTkCore.ttk import TTk

_CORE_EXCEPTHOOK = sys.excepthook
_CORE_UNRAISABLEHOOK = sys.unraisablehook
_CORE_THREADING_EXCEPTHOOK = threading.excepthook


class Application(TTk):

    def __init__(self, ci_mode):

        super().__init__(
            title=pynicotine.__application_name__,
            layout=TTkGridLayout(),
            # mouseTrack=True,
            # mouseCursor=True,
            # sigmask=(TTkTerm.Sigmask.CTRL_C | TTkTerm.Sigmask.CTRL_Q |
            #          TTkTerm.Sigmask.CTRL_S))  # | TTkTerm.Sigmask.CTRL_Z))
        )

        self.ci_mode = ci_mode

        sys.excepthook = self.on_critical_error
        sys.unraisablehook = self._raise_exception

        self.screen = None      # TTk Root Container will run in its own thread
        self.about = None
        self.fast_configure = None
        self.preferences = None
        self.chat_history = None
        self.room_list = None

        for event_name, callback in (
            ("start", self.on_startup),
            ("confirm-quit", self.on_confirm_quit),
            ("invalid-password", self.on_invalid_password),
            ("invalid-username", self.on_invalid_username),
            #("quit", self._instance.quit),
            ("server-login", self._update_user_status),
            ("server-disconnect", self._update_user_status),
            ("setup", self.on_fast_configure),
            ("shares-unavailable", self.on_shares_unavailable),
            #("show-notification", self._show_notification),
            #("show-chatroom-notification", self._show_chatroom_notification),
            #("show-download-notification", self._show_download_notification),
            #("show-private-chat-notification", self._show_private_chat_notification),
            #("show-search-notification", self._show_search_notification),
            #("show-upload-notification", self._show_upload_notification),
            ("user-status", self.on_user_status)
        ):
            events.connect(event_name, callback)

    def run(self):

        from pynicotine.ttktui.dialogs.chathistory import ChatHistory
        from pynicotine.ttktui.dialogs.roomlist import RoomList
        from pynicotine.ttktui.mainscreen import MainScreen
        from TermTk import __version__ as TTk_version

        self.screen = MainScreen(self)
        self.chat_history = ChatHistory(self)
        self.room_list = RoomList(self)

        core.start()

        log.add(_("Loaded %(program)s %(version)s"), {"program": "TTk", "version": TTk_version})

        if config.sections["server"]["auto_connect_startup"]:
            core.connect()

        # Main loop, process events from threads 10 times per second
        while events.process_thread_events():
            time.sleep(0.1)

        # Shut down with exit code 0 (success)
        self.on_shutdown()
        config.write_configuration()
        return 0

    def on_startup(self):
        #self.screen.start()
        self.screen.load()
        self.screen.start()

    # Primary Menus #

    def create_file_menu(self, header_menu, _position=None):

        self.file_menu = header_menu.addMenu(_("_File").replace("_", "&"))
        self.file_menu._connect = self.file_menu.addMenu(_("_Connect"))
        self.file_menu._connect.menuButtonClicked.connect(self.on_connect)
        self.file_menu._disconnect = self.file_menu.addMenu(_("_Disconnect"))
        self.file_menu._disconnect.menuButtonClicked.connect(self.on_disconnect)
        self.file_menu._privileges = self.file_menu.addMenu(_("Soulseek _Privileges"))

        self._update_user_status()

        self.file_menu.addSpacer()
        self.file_menu.addMenu(_("_Preferences")).menuButtonClicked.connect(self.on_preferences)
        self.file_menu.addSpacer()
        self.file_menu._quit = self.file_menu.addMenu(("_Quit"))
        self.file_menu._quit.menuButtonClicked.connect(self.on_confirm_quit_request)

    def create_shares_menu(self, header_menu, _position=None):

        self.shares_menu = header_menu.addMenu(_("_Shares").replace("_", "&"))
        self.shares_menu.addMenu(_("_Rescan Shares")).menuButtonClicked.connect(self.on_rescan_shares)
        self.shares_menu.addMenu(_("Configure _Shares")).menuButtonClicked.connect(self.on_configure_shares)
        self.shares_menu.addSpacer()
        self.shares_menu.addMenu(_("Browse _Public Shares")).menuButtonClicked.connect(self.on_browse_public_shares)
        self.shares_menu.addMenu(_("Browse _Buddy Shares")).menuButtonClicked.connect(self.on_browse_buddy_shares)
        self.shares_menu.addMenu(_("Browse _Trusted Shares")).menuButtonClicked.connect(self.on_browse_trusted_shares)

    def create_help_menu(self, header_menu, position=None):

        self.help_menu = header_menu.addMenu(_("_Help").replace("_", "&"), alignment=position)
        self.help_menu.addMenu(_("_Keyboard Shortcuts")).menuButtonClicked.connect(self.on_keyboard_shortcuts)
        self.help_menu.addMenu(_("_Setup Assistant")).menuButtonClicked.connect(self.on_fast_configure)
        self.help_menu.addMenu(_("_Transfer Statistics")).menuButtonClicked.connect(self.on_transfer_statistics)
        self.help_menu.addSpacer()
        self.help_menu.addMenu(_("Report a _Bug")).menuButtonClicked.connect(self.on_report_bug)
        self.help_menu.addMenu(_("Improve T_ranslations")).menuButtonClicked.connect(self.on_improve_translations)
        self.help_menu.addSpacer()
        self.help_menu.addMenu(_("_About Nicotine+").replace("_", "&")).menuButtonClicked.connect(self.on_about)

    def create_view_menu(self, tab_bar, position=None):

        self.view_menu = tab_bar.addMenu("◨", position=position)
        self.view_menu._sidebar = self.view_menu.addMenu(
            "Buddies Sidebar", checkable=True, checked=(config.sections["ui"]["buddylistinchatrooms"] != "tab")
        )
        self.view_menu._sidebar.menuButtonClicked.connect(self.screen.buddies.set_buddy_list_position)

    def create_log_menu(self, footer_menu, position=None):

        self.log_menu = footer_menu.addMenu(
            " ∴ ", checked=(not config.sections["logging"]["logcollapsed"]), alignment=position  # ⁝ ∵ ∴ ⌤
        )
        self.log_menu.menuButtonClicked.connect(self.screen.log_view.on_show_log_pane)
        self.log_menu.setToolTip(_("Show Log Pane"))

    def _update_user_status(self, *_args):

        is_online = (core.users.login_status != UserStatus.OFFLINE)

        for action in (self.file_menu._connect,):
            if action.isEnabled() != (not is_online):
                self.file_menu._connect.setEnabled(not is_online)

        # , "away-accel", "message-downloading-users", "message-buddies"):
        for action in (self.file_menu._disconnect, self.file_menu._privileges):
            if action.isEnabled() != is_online:
                action.setEnabled(is_online)

    def on_user_status(self, msg):
        if msg.user == core.users.login_username:
            self._update_user_status()

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
                (OptionDialog.StandardButton.Cancel, _("_No")),
                (OptionDialog.StandardButton.Yes, _("_Quit")),
                (OptionDialog.StandardButton.Save, _("_Run in Background"))
            ],
            default_button=OptionDialog.StandardButton.Cancel,
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

    # Actions #

    def on_away(self, *_args):
        """Away/Online status button."""

        if core.users.login_status == UserStatus.OFFLINE:
            core.connect()
            return

        core.users.set_away_mode(core.users.login_status != UserStatus.AWAY, save_state=True)

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

    def on_fast_configure(self, *_args, invalid_password=False, invalid_username=False):

        if self.fast_configure is None:
            from pynicotine.ttktui.dialogs.fastconfigure import FastConfigure
            self.fast_configure = FastConfigure(self)

        elif self.fast_configure.window is not None:
            self.fast_configure.close()

        #if invalid_password and self.fast_configure.is_visible():
        #    self.fast_configure.hide()

        change_account = invalid_password or invalid_username
        self.fast_configure.invalid_password = invalid_password
        self.fast_configure.invalid_username = invalid_username

        if change_account:
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

    def on_report_bug(*_args):
        pass  #

    def on_improve_translations(*_args):
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

    def on_browse_public_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.PUBLIC, new_request=True)

    def on_browse_buddy_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.BUDDY, new_request=True)

    def on_browse_trusted_shares(self, *_args):
        core.userbrowse.browse_local_shares(permission_level=PermissionLevel.TRUSTED, new_request=True)

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
        #if self.screen is not None:
        #    self.screen.join(timeout=1)

        events.process_thread_events()

        # Log exception in terminal
        self._raise_exception(exc_value)

    @staticmethod
    def _raise_exception(exc_value):

        from traceback import format_exc
        print(exc_value)
        print(format_exc())

        # Also show errors from further down the stack
        sys.excepthook = _CORE_EXCEPTHOOK
        sys.unraisablehook = _CORE_UNRAISABLEHOOK
        threading.excepthook = _CORE_THREADING_EXCEPTHOOK
        raise BaseException(exc_value)

    def on_critical_error(self, exc_type, exc_value, exc_traceback):

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

    #def on_force_quit_request(self, *_args):
    #    core.quit()

    def on_quit_request(self, *_args):

        if not core.uploads.has_active_uploads():
            core.quit()
            return

        core.confirm_quit()

    def on_shutdown(self, *_args):

        if self.about is not None:
            self.about.destroy()

        if self.fast_configure is not None:
            self.fast_configure.destroy()

        if self.preferences is not None:
            self.preferences.destroy()

        if self.chat_history is not None:
            self.chat_history.destroy()

        if self.room_list is not None:
            self.room_list.destroy()

        if self.screen is not None:
            self.screen.destroy()

        self.__dict__.clear()
