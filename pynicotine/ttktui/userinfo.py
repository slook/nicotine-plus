# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2010 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.slskmessages import ConnectionType
from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.interests import InterestsPicker
from pynicotine.ttktui.widgets.dialogs import EntryDialog
from pynicotine.ttktui.widgets.dialogs import MessageDialog
from pynicotine.ttktui.widgets.pages import Pages
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS
from pynicotine.utils import humanize
from pynicotine.utils import human_speed


class UserInfos(Pages):

    def __init__(self, screen, name="userinfo"):

        self.screen = screen

        super().__init__(self, name)

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        _expander_left = ttk.TTkSpacer(parent=self.header_bar)

        self.userinfo_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(">", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
        )
        self.userinfo_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.userinfo_button.clicked.connect(self.on_userinfo_clicked)

        self.userinfo_combobox = ttk.TTkComboBox(parent=self.header_bar, editable=True, insertPolicy=ttk.TTkK.NoInsert)
        self.userinfo_combobox.lineEdit()._hint = ttk.TTkString(_("Username…"))
        self.userinfo_combobox.setMinimumWidth(core.users.USERNAME_MAX_LENGTH + 4)
        self.userinfo_combobox.setMaximumWidth(core.users.USERNAME_MAX_LENGTH + 4)
        self.userinfo_combobox.currentIndexChanged.connect(self.on_userinfo_pressed)

        _expander_right = ttk.TTkSpacer(parent=self.header_bar)

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout())
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[name]
        )
        _placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN,
            text=_("Enter the name of a user to view their user description, "
                   "information and personal picture").replace(", ", ",\n")
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        for widget in [self.userinfo_button, self.userinfo_combobox.lineEdit()]:
            widget.setToolTip(_placeholder.text())

        # Events
        for event_name, callback in (
            ("add-buddy", self.add_remove_buddy),
            ("ban-user", self.ban_unban_user),
            ("check-privileges", self.check_privileges),
            ("ignore-user", self.ignore_unignore_user),
            ("peer-connection-closed", self.peer_connection_error),
            ("peer-connection-error", self.peer_connection_error),
            #("quit", self.quit),
            ("remove-buddy", self.add_remove_buddy),
            ("server-disconnect", self.server_disconnect),
            ("unban-user", self.ban_unban_user),
            ("unignore-user", self.ignore_unignore_user),
            ("user-country", self.user_country),
            ("user-info-progress", self.user_info_progress),
            ("user-info-remove-user", self.remove_user),
            ("user-info-response", self.user_info_response),
            ("user-info-show-user", self.show_user),
            ("user-interests", self.user_interests),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def quit(self):
        self.userinfo_button.clicked.disconnect(self.on_userinfo_clicked)
        self.userinfo_combobox.currentIndexChanged.disconnect(self.on_userinfo_pressed)
        self.userinfo_combobox.clearFocus()
        self.userinfo_combobox.close()
        super().destroy()

    def focus_default_widget(self):
        self.userinfo_combobox.setFocus()

    def on_remove_all_pages(self, *_args):
        core.userinfo.remove_all_users()

    def on_restore_removed_page(self, page_args):
        username, = page_args
        core.userinfo.show_user(username)

    @ttk.pyTTkSlot(int)
    def on_switch_page(self, page_number):

        if self.screen.tab_bar.currentWidget() != self:
            return

        self.focus_default_widget()

        page = self.widget(page_number)

        if not page:
            return

        self.remove_tab_changed(page)

    @ttk.pyTTkSlot(int)  # Enter
    def on_userinfo_pressed(self, _id):
        self.on_get_page(self.userinfo_combobox)

    @ttk.pyTTkSlot()  # Mouse
    def on_userinfo_clicked(self):

        if not self.userinfo_combobox.currentText():
            self.userinfo_combobox.setFocus()
            return

        self.on_get_page(self.userinfo_combobox)

    #def on_show_user_profile(self, *_args):
    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_get_page(self, caller):

        if isinstance(caller, ttk.TTkMenuButton):
            username = caller.data()
        else:
            username = str(caller.currentText()).strip()
            caller.setEditText("")

        if not username:
            return

        core.userinfo.show_user(username)

    def show_user(self, user, refresh=False, switch_page=True):

        page = self.pages.get(user)

        if page is None:
            self.pages[user] = page = UserInfo(self, user)

            page_index = self.addTab(page, f"   {user}", data=user)
            page_button = self.tabButton(page_index)
            page_button.closeClicked.connect(page.on_close)
            #page_button.rightButtonClicked.connect(self.on_page_menu)

            user_status = core.users.statuses.get(user, UserStatus.OFFLINE)
            self.set_user_status(user, user_status)
            #page.user_status(user_status)

            self.update_pages_menu_item(user)
            self.update_pages_count()

        if switch_page:
            self.setCurrentWidget(page)
            self.screen.tab_bar.setCurrentWidget(self.screen.tabs["userinfo"])

        if refresh:
            page.set_indeterminate_progress()
            page.populate_stats()

    def remove_user(self, user):

        page = self.pages.get(user)

        if page is None:
            return

        self.remove_page(page, page_args=(user,))

    def check_privileges(self, _msg):
        for page in self.pages.values():
            page.update_privileges_button_state()

    def ban_unban_user(self, user):

        page = self.pages.get(user)

        if page is not None:
            page.update_ban_button_state()

    def ignore_unignore_user(self, user):

        page = self.pages.get(user)

        if page is not None:
            page.update_ignore_button_state()

    def add_remove_buddy(self, user, *_args):

        page = self.pages.get(user)

        if page is not None:
            page.update_buddy_button_state()

    def peer_connection_error(self, username, conn_type, **_unused):

        page = self.pages.get(username)

        if page is None:
            return

        if conn_type == ConnectionType.PEER:
            page.peer_connection_error()

    def user_stats(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            page.user_stats(msg)

    def user_status(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            self.set_user_status(msg.user, msg.status)
            page.user_status(msg)

    def user_country(self, user, country_code):

        page = self.pages.get(user)

        if page is not None:
            page.user_country(country_code)

    def user_interests(self, msg):

        page = self.pages.get(msg.user)

        if page is not None:
            page.user_interests(msg)

    def user_info_progress(self, user, _sock, position, total):

        page = self.pages.get(user)

        if page is not None:
            page.user_info_progress(position, total)

    def user_info_response(self, msg):

        page = self.pages.get(msg.username)

        if page is not None:
            page.user_info_response(msg)

    def server_disconnect(self, *_args):
        for user, page in self.pages.items():
            #page.user_status(UserStatus.OFFLINE)
            self.set_user_status(user, UserStatus.OFFLINE)


class UserInfo(ttk.TTkContainer):

    def __init__(self, userinfos, user):
        super().__init__(layout=ttk.TTkVBoxLayout(), name=user)

        self.userinfos = userinfos
        self.screen = userinfos.screen

        self.progress_container = ttk.TTkContainer(parent=self, layout=ttk.TTkHBoxLayout(), minHeight=1, maxHeight=1, visible=False)
        self.info_bar_container = ttk.TTkContainer(parent=self, layout=ttk.TTkLayout(), minHeight=1, maxHeight=1, visible=False)

        self.userinfo_container = ttk.TTkContainer(parent=self, layout=ttk.TTkHBoxLayout())

        self.content_container = ttk.TTkSplitter(parent=self.userinfo_container, name=userinfos.name())  # "userinfo"

        self.profile_frame = ttk.TTkFrame(parent=self.content_container, layout=ttk.TTkVBoxLayout(), title=user)
        status_box = ttk.TTkContainer(parent=self.profile_frame, layout=ttk.TTkHBoxLayout(), padding=(1,1,1,1))
        self.privileged_user_button = ttk.TTkButton(parent=status_box, text=_("Privileged User"), visible=False)
        self.privileged_user_button.clicked.connect(self.on_privileged_user)
        status_captions = ttk.TTkContainer(parent=status_box, layout=ttk.TTkVBoxLayout(), paddingRight=2)
        status_labels = ttk.TTkContainer(parent=status_box, layout=ttk.TTkVBoxLayout(), paddingLeft=2)
        status_captions.layout().addWidget(
            ttk.TTkLabel(text=_("Status"), color=ttk.TTkColor.ITALIC, alignment=ttk.TTkK.RIGHT_ALIGN, maxHeight=1))
        self.user_status_label = ttk.TTkLabel(parent=status_labels, text=_("Unknown"))

        self.description_frame = ttk.TTkFrame(
            parent=self.profile_frame, layout=ttk.TTkGridLayout(), title="Description", titleAlign=ttk.TTkK.LEFT_ALIGN)
        self.description_view = ttk.TTkTextEdit(parent=self.description_frame, readOnly=True)
        self.description_view.setLineWrapMode(ttk.TTkK.WidgetWidth)
        self.description_view.setWordWrapMode(ttk.TTkK.WordWrap)

        profile_box = ttk.TTkContainer(parent=self.profile_frame, layout=ttk.TTkHBoxLayout(), padding=(1,1,1,1))
        profile_captions = ttk.TTkContainer(parent=profile_box, layout=ttk.TTkVBoxLayout(), paddingRight=2)
        profile_labels = ttk.TTkContainer(parent=profile_box, layout=ttk.TTkVBoxLayout(), paddingLeft=2)

        for text in [
            _("Country"), _("Shared Files"), _("Shared Folders"), _("Upload Speed"),
            _("Upload Slot Available"), _("Upload Slots"), _("Queued Uploads")
        ]:
            profile_captions.layout().addWidget(
                ttk.TTkLabel(text=text, color=ttk.TTkColor.ITALIC, alignment=ttk.TTkK.RIGHT_ALIGN, minHeight=1, maxHeight=1))

        self.country_label = ttk.TTkLabel(parent=profile_labels, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.shared_files_label = ttk.TTkLabel(parent=profile_labels, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.shared_folders_label = ttk.TTkLabel(parent=profile_labels, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.upload_speed_label = ttk.TTkLabel(parent=profile_labels, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.free_upload_slots_label = ttk.TTkLabel(parent=profile_labels, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.upload_slots_label = ttk.TTkLabel(parent=profile_labels, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.queued_uploads_label = ttk.TTkLabel(parent=profile_labels, text=_("Unknown"), color=ttk.TTkColor.BOLD)

        self.interests_picker = InterestsPicker(
            parent=self.content_container,  # editable=(user == config.sections["server"]["login"]),
            recommend_callback=self.screen.interests.show_item_recommendations
        )

        self.buttons_frame = ttk.TTkFrame(
            parent=self.userinfo_container, maxWidth=30, layout=ttk.TTkVBoxLayout(), title=_("User Actions")
        )
        scroll_area = ttk.TTkScrollArea(parent=self.buttons_frame, horizontalScrollBarPolicy=ttk.TTkK.ScrollBarAlwaysOff)
        self.buttons_box = ttk.TTkContainer(parent=scroll_area.viewport(), layout=ttk.TTkVBoxLayout())

        self._send_message_button = ttk.TTkButton(parent=self.buttons_box, text=_("_Send Message"), border=True, maxHeight=3)
        self._send_message_button.clicked.connect(self.on_send_message)

        self._browse_files_button = ttk.TTkButton(parent=self.buttons_box, text=_("_Browse Files"), border=True, maxHeight=3)
        self._browse_files_button.clicked.connect(self.on_browse_user)

        self.add_remove_buddy_button = ttk.TTkButton(parent=self.buttons_box, border=True, maxHeight=3)
        self.add_remove_buddy_button.clicked.connect(self.on_add_remove_buddy)

        self.ban_unban_user_button = ttk.TTkButton(parent=self.buttons_box, border=True, maxHeight=3)
        self.ban_unban_user_button.clicked.connect(self.on_ban_unban_user)

        self.ignore_unignore_user_button = ttk.TTkButton(parent=self.buttons_box, border=True, maxHeight=3)
        self.ignore_unignore_user_button.clicked.connect(self.on_ignore_unignore_user)

        self.show_ip_address_button = ttk.TTkButton(parent=self.buttons_box, text="Show IP Address", border=True, maxHeight=3)
        self.show_ip_address_button.clicked.connect(self.on_show_ip_address)

        self.gift_privileges_button = ttk.TTkButton(
            parent=self.buttons_box, text=_("_Gift Privileges…"), border=True, maxHeight=3)
        self.gift_privileges_button.clicked.connect(self.on_give_privileges)

        _buttons_spacer = ttk.TTkSpacer(parent=self.buttons_box, minHeight=1)

        self.save_picture_button = ttk.TTkFileButtonPicker(
            parent=self.buttons_box,
            caption=_("_Save Picture").replace("_", ""),
            path=core.downloads.get_default_download_folder(),
            acceptMode=ttk.TTkK.AcceptMode.AcceptSave,
            fileMode=ttk.TTkK.FileMode.AnyFile,
            enabled=False
        )
        self.save_picture_button.setText(_("_Save Picture"))
        self.save_picture_button.folderPicked.connect(self.on_save_picture_response)

        self.refresh_button = ttk.TTkButton(parent=self.buttons_box, text="↻ Refresh", border=True, maxHeight=3)
        self.refresh_button.clicked.connect(self.on_refresh)

        self.progress_bar = ttk.TTkFancyProgressBar(parent=self.progress_container)
        self.info_bar = ttk.TTkLabel(parent=self.info_bar_container, alignment=ttk.TTkK.CENTER_ALIGN)

        self.content_container.setSizes([None, min(43, self.screen.width() / 4)])

        @ttk.pyTTkSlot(int, int)
        def on_resize(w, _h):
            self.buttons_box.setGeometry(
                1,
                0,
                self.buttons_frame.width()-4,
                max(self.buttons_frame.height()-2, self.buttons_box.minimumHeight())
            )
            self.info_bar_container.setGeometry(0, 0, w, 1)
            self.info_bar.setGeometry(0, 0, w, 1)

        self.sizeChanged.connect(on_resize)

        self.user = user
        self.picture_bytes = None
        #self.picture_data = None
        #self.picture_surface = None
        self.indeterminate_progress = False
        self.refreshing = False

        self.populate_stats()
        self.update_button_states()

    def destroy(self):

        self.privileged_user_button.clicked.disconnect(self.on_privileged_user)
        self._send_message_button.clicked.disconnect(self.on_send_message)
        self._browse_files_button.clicked.disconnect(self.on_browse_user)
        self.add_remove_buddy_button.clicked.disconnect(self.on_add_remove_buddy)
        self.ban_unban_user_button.clicked.disconnect(self.on_ban_unban_user)
        self.ignore_unignore_user_button.clicked.disconnect(self.on_ignore_unignore_user)
        self.show_ip_address_button.clicked.disconnect(self.on_show_ip_address)
        self.save_picture_button.folderPicked.disconnect(self.on_save_picture_response)
        self.refresh_button.clicked.disconnect(self.on_refresh)

        self.clear()
        self.layout().clear()
        self.interests_picker.close()
        self.close()

    def clear(self):
        self.description_view.setText("")
        self.interests_picker.clear()

    @ttk.pyTTkSlot()
    def on_close(self, *_args):
        core.userinfo.remove_user(self.user)

    # General #

    def populate_stats(self):

        country_code = core.users.countries.get(self.user)
        stats = core.users.watched.get(self.user)
        status = core.users.statuses.get(self.user, UserStatus.OFFLINE)
        status_icon = USER_STATUS_ICONS.get(status)
        status_text = USER_STATUS_LABELS.get(status)

        self.user_status_label.setText(status_icon + ttk.TTkColor.RST + ttk.TTkColor.BOLD + status_text)

        if stats is not None:
            speed = stats.upload_speed or 0
            files = stats.files
            folders = stats.folders
        else:
            speed = 0
            files = folders = None

        if speed > 0:
            self.upload_speed_label.setText(human_speed(speed))

        if files is not None:
            self.shared_files_label.setText(humanize(files))

        if folders is not None:
            self.shared_folders_label.setText(humanize(folders))

        if country_code:
            self.user_country(country_code)

    def peer_connection_error(self):

        if not self.refreshing:
            return

        if core.users.statuses.get(self.user, UserStatus.OFFLINE) == UserStatus.OFFLINE:
            error_message = _("Cannot request information from the user, since they are offline.")
        else:
            error_message = _("Cannot request information from the user, possibly due to "
                              "a closed listening port or temporary connectivity issue.")

        self.info_bar.setText(error_message)
        self.info_bar.setColor(ttk.TTkColor.BOLD + ttk.TTkColor.WHITE + ttk.TTkColor.BG_RED)
        self.info_bar_container.setVisible(True)
        self.set_finished()

    def pulse_progress(self, repeat=True):

        class Pl(ttk.TTkLookAndFeelFPBar):
            def color(self, value, maximum, minimum):
                return ttk.TTkColor.fg("#000000") + ttk.TTkColor.bg("#FFAA40")

        class Pr(ttk.TTkLookAndFeelFPBar):
            def color(self, value, maximum, minimum):
                return ttk.TTkColor.fg("#FFAA40") + ttk.TTkColor.bg("#000000")

        pulser_left = ttk.TTkFancyProgressBar(parent=self.progress_container, value=1, lookAndFeel=Pl(showText=False))
        pulser_right = ttk.TTkFancyProgressBar(parent=self.progress_container, lookAndFeel=Pr(showText=False))

        def pulse():
            if not self.indeterminate_progress:  # repeat
                pulser_left.close()
                pulser_right.close()
                self.progress_bar.show()
                return

            if self.progress_bar.isVisible():
                self.progress_bar.hide()

            last_value = pulser_left.value()
            pulser_left.setValue(1 if last_value == 0 else last_value - 0.05)
            pulser_right.setValue(1 - pulser_left.value())
            timer.start(0.1)

        timer = ttk.TTkTimer()
        timer.timeout.connect(pulse)
        timer.start(0.1)

    def user_info_progress(self, position, total):

        if not self.refreshing:
            return

        self.indeterminate_progress = False

        if total <= 0 or position <= 0:
            fraction = 0.0

        elif position < total:
            fraction = float(position) / total

        else:
            fraction = 1.0

        self.progress_bar.setValue(fraction)

    def set_indeterminate_progress(self):

        if self.indeterminate_progress:
            return

        self.indeterminate_progress = self.refreshing = True

        if core.users.login_status == UserStatus.OFFLINE and self.user != config.sections["server"]["login"]:
            self.peer_connection_error()
            return

        self.refresh_button.setEnabled(False)
        self.info_bar_container.setVisible(False)
        self.progress_container.setVisible(True)
        self.pulse_progress()

    def set_finished(self):

        self.indeterminate_progress = self.refreshing = False

        self.userinfos.request_tab_changed(self)
        self.progress_bar.setValue(1.0)
        self.progress_container.setVisible(False)

        self.refresh_button.setEnabled(True)

    # Button States #

    def update_local_buttons_state(self):

        local_username = core.users.login_username or config.sections["server"]["login"]

        #for widget in (self.edit_interests_button, self.edit_profile_button):
        #    widget.set_visible(self.user == local_username)

        for widget in (self.ban_unban_user_button, self.ignore_unignore_user_button):
            widget.setVisible(self.user != local_username)

    def update_buddy_button_state(self):
        label = _("Remove _Buddy") if self.user in core.buddies.users else _("Add _Buddy")
        self.add_remove_buddy_button.setText(label)
        #self.add_remove_buddy_label.set_text_with_mnemonic(label)

    def update_ban_button_state(self):
        label = _("Unban User") if core.network_filter.is_user_banned(self.user) else _("Ban User")
        self.ban_unban_user_button.setText(label)

    def update_ignore_button_state(self):
        label = _("Unignore User") if core.network_filter.is_user_ignored(self.user) else _("Ignore User")
        self.ignore_unignore_user_button.setText(label)

    def update_privileges_button_state(self):
        self.gift_privileges_button.setEnabled(bool(core.users.privileges_left))

    def update_button_states(self):

        self.update_local_buttons_state()
        self.update_buddy_button_state()
        self.update_ban_button_state()
        self.update_ignore_button_state()
        self.update_privileges_button_state()

    # Network Messages #

    def user_info_response(self, msg):

        if not self.refreshing:
            return

        if msg is None:
            return

        if msg.descr is not None:
            self.description_view.setText(msg.descr)

        self.free_upload_slots_label.setText(_("Yes") if msg.slotsavail else _("No"))
        self.upload_slots_label.setText(humanize(msg.totalupl))
        self.queued_uploads_label.setText(humanize(msg.queuesize))

        self.picture_bytes = msg.pic
        self.save_picture_button.setEnabled(bool(self.picture_bytes))

        self.info_bar.setVisible(False)
        self.set_finished()

    def user_status(self, msg):

        status_icon = USER_STATUS_ICONS.get(msg.status)
        status_text = USER_STATUS_LABELS.get(msg.status)

        self.user_status_label.setText(status_icon + ttk.TTkColor.RST + ttk.TTkColor.BOLD + status_text)
        self.privileged_user_button.setVisible(msg.privileged)

    def user_stats(self, msg):

        speed = msg.avgspeed or 0
        num_files = msg.files or 0
        num_folders = msg.dirs or 0

        h_speed = human_speed(speed) if speed > 0 else _("Unknown")
        h_num_files = humanize(num_files)
        h_num_folders = humanize(num_folders)

        if self.upload_speed_label.text() != h_speed:
            self.upload_speed_label.setText(h_speed)

        if self.shared_files_label.text() != h_num_files:
            self.shared_files_label.setText(h_num_files)

        if self.shared_folders_label.text() != h_num_folders:
            self.shared_folders_label.setText(h_num_folders)

    def user_country(self, country_code):

        if not country_code:
            return

        country_name = core.network_filter.COUNTRIES.get(country_code, _("Unknown"))

        self.country_label.setText(country_code)
        self.country_label.setToolTip(f"{country_name} ({country_code})")

    def user_interests(self, msg):
        self.interests_picker.populate_interests(likes=msg.likes, hates=msg.hates)

    # Callbacks #

    def on_show_ip_address(self):
        core.users.request_ip_address(self.user, notify=True)

    def on_send_message(self):
        core.privatechat.show_user(self.user)

    def on_browse_user(self):
        core.userbrowse.browse_user(self.user)

    def on_add_remove_buddy(self):

        if self.user in core.buddies.users:
            core.buddies.remove_buddy(self.user)
            return

        core.buddies.add_buddy(self.user)

    def on_ban_unban_user(self):

        if core.network_filter.is_user_banned(self.user):
            core.network_filter.unban_user(self.user)
            return

        core.network_filter.ban_user(self.user)

    def on_ignore_unignore_user(self):

        if core.network_filter.is_user_ignored(self.user):
            core.network_filter.unignore_user(self.user)
            return

        core.network_filter.ignore_user(self.user)

    def on_privileged_user(self):
        #log.add
        MessageDialog(
            parent=self.screen,
            title=_("Privileged User"),
            message=(_("User %(user)s has Soulseek privileges. Their downloads are queued ahead "
                       "of those of non-privileged users.") % {"user": self.user})
        ).present()

    def on_give_privileges(self, *_args, error=None):

        def response(dialog, _response_id, _data):

            days = dialog.get_entry_value()

            if not days:
                return

            try:
                days = int(days)

            except ValueError:
                self.on_give_privileges(error=_("Please enter number of days."))
                return

            core.users.request_give_privileges(self.user, days)

        core.users.request_check_privileges()

        if core.users.privileges_left is None:
            days = _("Unknown")
        else:
            days = core.users.privileges_left // 60 // 60 // 24

        message = (_("Gift days of your Soulseek privileges to user %(user)s (%(days_left)s):") %
                   {"user": self.user + "\n\n", "days_left": _("%(days)s days left") % {"days": days}})

        if error:
            message += "\n\n" + error

        EntryDialog(
            parent=self.screen,
            title=_("Gift Privileges"),
            message=message,
            action_button_label=_("_Send"),
            callback=response
        ).present()

    @ttk.pyTTkSlot(str)
    def on_save_picture_response(self, file_path):
        core.userinfo.save_user_picture(file_path, picture_bytes)

    def on_refresh(self):
        core.userinfo.show_user(self.user, refresh=True)
