# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2010 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-FileCopyrightText: 2003-2004 Nicotine Contributors
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
from pynicotine.ttktui.widgets.tabs import Pages
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS
from pynicotine.utils import humanize
from pynicotine.utils import human_size
from pynicotine.utils import human_speed


class UserInfos(Pages):

    def __init__(self, screen, name="userinfo"):

        self.screen = screen

        super().__init__(self, name)

        self.userinfo_combobox = ttk.TTkComboBox(editable=True, insertPolicy=ttk.TTkK.NoInsert)
        self.userinfo_combobox.lineEdit()._hint = ttk.TTkString(_("Username…"))
        self.userinfo_combobox.setMinimumWidth(core.users.USERNAME_MAX_LENGTH + 4)
        self.userinfo_combobox.setMaximumWidth(core.users.USERNAME_MAX_LENGTH + 4)

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout())
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[name]
        )
        self._placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN,
            text=_("Enter the name of a user to view their user description, "
                   "information and personal picture").replace(", ", ",\n")
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        # Events
        for event_name, callback in (
            ("add-buddy", self.add_remove_buddy),
            ("ban-user", self.ban_unban_user),
            ("check-privileges", self.check_privileges),
            ("ignore-user", self.ignore_unignore_user),
            ("peer-connection-closed", self.peer_connection_error),
            ("peer-connection-error", self.peer_connection_error),
            # ("quit", self.quit),
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

    def create_header(self):

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        _expander_left = ttk.TTkSpacer(parent=self.header_bar)

        self.userinfo_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(">", ttk.TTkColor.BOLD),
            minWidth=5, maxWidth=5, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
        )
        self.userinfo_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.userinfo_button.clicked.connect(self.on_userinfo_clicked)

        self.header_bar.layout().addWidget(self.userinfo_combobox)
        self.userinfo_combobox.currentIndexChanged.connect(self.on_userinfo_pressed)

        _expander_right = ttk.TTkSpacer(parent=self.header_bar)

        for widget in (self.userinfo_button, self.userinfo_combobox.lineEdit()):
            widget.setToolTip(self._placeholder.text())

    def destroy(self):
        self.userinfo_button.clicked.disconnect(self.on_userinfo_clicked)
        self.userinfo_combobox.currentIndexChanged.disconnect(self.on_userinfo_pressed)
        self.userinfo_combobox.clearFocus()
        self.userinfo_combobox.close()
        super().destroy()

    def focus_default_widget(self):

        if self.screen.tab_bar.currentWidget() != self:
            return

        page = self.currentWidget()

        if isinstance(page, UserInfo) and not page.description_view.isReadOnly():
            page.description_view.setFocus()
        else:
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

        self.screen.focus_default_widget()

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

    # def on_show_user_profile(self, *_args):
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
            # page_button.rightButtonClicked.connect(self.on_page_menu)

            user_status = core.users.statuses.get(user, UserStatus.OFFLINE)
            self.set_user_status(user, user_status)
            # page.user_status(user_status)

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
            self.set_user_status(user, UserStatus.OFFLINE)
            page.user_status(None)  # "Unknown"


class UserInfo(ttk.TTkContainer):

    def __init__(self, userinfos, user):
        super().__init__(layout=ttk.TTkVBoxLayout(), name=user)

        self.userinfos = userinfos
        self.screen = userinfos.screen

        self.userinfo_container = ttk.TTkContainer(parent=self, layout=ttk.TTkHBoxLayout())
        self.content_container = ttk.TTkSplitter(parent=self.userinfo_container, name=userinfos.name())  # "userinfo"

        self.profile_frame = ttk.TTkFrame(parent=self.content_container, layout=ttk.TTkVBoxLayout(), title=user)

        self.privileged_user_button = ttk.TTkButton(parent=self.profile_frame, text=_("Privileged User"), visible=False)
        self.privileged_user_button.clicked.connect(self.on_privileged_user)

        status_box = ttk.TTkContainer(parent=self.profile_frame, layout=ttk.TTkHBoxLayout(), padding=(1, 1, 1, 1))

        country_captions = ttk.TTkContainer(parent=status_box, layout=ttk.TTkVBoxLayout(), paddingRight=3)
        country_labels = ttk.TTkContainer(parent=status_box, layout=ttk.TTkHBoxLayout(), paddingRight=2)
        country_captions.layout().addWidgets([
            ttk.TTkLabel(text=_("Country"), color=ttk.TTkColor.ITALIC, alignment=ttk.TTkK.RIGHT_ALIGN, maxHeight=1)
        ])
        self.country_label = ttk.TTkLabel(parent=country_labels, text=_("Unknown"), color=ttk.TTkColor.BOLD)

        status_captions = ttk.TTkContainer(parent=status_box, layout=ttk.TTkVBoxLayout())
        status_labels = ttk.TTkContainer(parent=status_box, layout=ttk.TTkVBoxLayout())
        status_captions.layout().addWidgets([
            ttk.TTkLabel(text=_("Status"), color=ttk.TTkColor.ITALIC, alignment=ttk.TTkK.RIGHT_ALIGN, maxHeight=1),
        ])
        self.user_status_label = ttk.TTkLabel(parent=status_labels, text=_("Unknown"))

        self.description_frame = ttk.TTkFrame(
            parent=self.profile_frame, layout=ttk.TTkVBoxLayout(), title="Description", titleAlign=ttk.TTkK.CENTER_ALIGN
        )
        self.description_view = ttk.TTkTextEdit(parent=self.description_frame, readOnly=True)
        self.description_view.setWordWrapMode(ttk.TTkK.WordWrap)
        self.description_view.setLineWrapMode(ttk.TTkK.WidgetWidth, wrapEngine=ttk.TTkK.WrapEngine.FastWrap)

        self.stats_container = ttk.TTkContainer(parent=self.profile_frame, layout=ttk.TTkVBoxLayout(),
                                                padding=(1, 1, 1, 1))
        self.stats_container.orientation = None

        stats_box_a = ttk.TTkContainer(parent=self.stats_container, layout=ttk.TTkHBoxLayout())
        stats_captions_a = ttk.TTkContainer(parent=stats_box_a, layout=ttk.TTkVBoxLayout(), paddingRight=3)
        stats_labels_a = ttk.TTkContainer(parent=stats_box_a, layout=ttk.TTkVBoxLayout())

        for text in (_("Shared Files"), _("Shared Folders"), _("Upload Speed")):
            stats_captions_a.layout().addWidget(
                ttk.TTkLabel(text=text, color=ttk.TTkColor.ITALIC, alignment=ttk.TTkK.RIGHT_ALIGN, maxHeight=1))

        self.shared_files_label = ttk.TTkLabel(parent=stats_labels_a, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.shared_folders_label = ttk.TTkLabel(parent=stats_labels_a, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.upload_speed_label = ttk.TTkLabel(parent=stats_labels_a, text=_("Unknown"), color=ttk.TTkColor.BOLD)

        stats_box_b = ttk.TTkContainer(parent=self.stats_container, layout=ttk.TTkHBoxLayout())
        stats_captions_b = ttk.TTkContainer(parent=stats_box_b, layout=ttk.TTkVBoxLayout(), paddingRight=3)
        stats_labels_b = ttk.TTkContainer(parent=stats_box_b, layout=ttk.TTkVBoxLayout())

        for text in (_("Upload Slot Available"), _("Upload Slots"), _("Queued Uploads")):
            stats_captions_b.layout().addWidget(
                ttk.TTkLabel(text=text, color=ttk.TTkColor.ITALIC, alignment=ttk.TTkK.RIGHT_ALIGN, maxHeight=1))

        self.free_upload_slots_label = ttk.TTkLabel(parent=stats_labels_b, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.upload_slots_label = ttk.TTkLabel(parent=stats_labels_b, text=_("Unknown"), color=ttk.TTkColor.BOLD)
        self.queued_uploads_label = ttk.TTkLabel(parent=stats_labels_b, text=_("Unknown"), color=ttk.TTkColor.BOLD)

        self.interests_picker = InterestsPicker(
            parent=self.content_container,  # editable=(user == config.sections["server"]["login"]),
            recommend_callback=self.screen.interests.show_item_recommendations
        )

        self.buttons_frame = ttk.TTkFrame(
            parent=self.userinfo_container, maxWidth=30, layout=ttk.TTkVBoxLayout(), title=_("User Actions")
        )
        scroll_area = ttk.TTkScrollArea(
            parent=self.buttons_frame, horizontalScrollBarPolicy=ttk.TTkK.ScrollBarAlwaysOff
        )
        self.buttons_box = ttk.TTkContainer(parent=scroll_area.viewport(), layout=ttk.TTkVBoxLayout())

        self.send_message_button = ttk.TTkButton(
            parent=self.buttons_box, text=_("_Send Message"), border=True, maxHeight=3
        )
        self.send_message_button.clicked.connect(self.on_send_message)

        self.browse_files_button = ttk.TTkButton(
            parent=self.buttons_box, text=_("_Browse Files"), border=True, maxHeight=3
        )
        self.browse_files_button.clicked.connect(self.on_browse_user)

        self.add_remove_buddy_button = ttk.TTkButton(parent=self.buttons_box, border=True, maxHeight=3)
        self.add_remove_buddy_button.clicked.connect(self.on_add_remove_buddy)

        self.ban_unban_user_button = ttk.TTkButton(parent=self.buttons_box, border=True, maxHeight=3)
        self.ban_unban_user_button.clicked.connect(self.on_ban_unban_user)

        self.ignore_unignore_user_button = ttk.TTkButton(parent=self.buttons_box, border=True, maxHeight=3)
        self.ignore_unignore_user_button.clicked.connect(self.on_ignore_unignore_user)

        self.show_ip_address_button = ttk.TTkButton(
            parent=self.buttons_box, text="Show IP Address", border=True, maxHeight=3
        )
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
        self.save_picture_button.filePicked.connect(self.on_save_picture_response)

        self.select_picture_button = ttk.TTkFileButtonPicker(
            parent=self.buttons_box,
            caption=_("Select an Image"),
            path=config.sections["userinfo"]["pic"],
            acceptMode=ttk.TTkK.AcceptMode.AcceptOpen,
            fileMode=ttk.TTkK.FileMode.ExistingFile
        )
        # self.select_picture_button.setPath(config.sections["userinfo"]["pic"])
        # self.select_picture_button.setText(_("Picture:"))
        self.select_picture_button.setToolTip(self.select_picture_button.path())
        self.select_picture_button.filePicked.connect(self.on_select_picture_response)

        self.refresh_button = ttk.TTkButton(
            parent=self.buttons_box,
            text=f'↻ {_("_Refresh Profile")}' if user != config.sections["server"]["login"] else "↶ Revert Changes",
            border=True,
            maxHeight=3
        )
        self.refresh_button.clicked.connect(self.on_refresh)

        self.save_profile_button = ttk.TTkButton(
            parent=self.buttons_box,
            text=f'↯ {_("%s Settings") % "_Save"}',  # f'↯ {_("_Apply")}',
            border=True,
            maxHeight=3,
            visible=False,
            enabled=False
        )

        self.progress_container = ttk.TTkContainer(
            parent=self, layout=ttk.TTkHBoxLayout(), minHeight=1, maxHeight=1, visible=False
        )
        self.progress_bar = ttk.TTkFancyProgressBar(parent=self.progress_container)

        self.info_bar_container = ttk.TTkContainer(
            parent=self, layout=ttk.TTkLayout(), minHeight=1, maxHeight=1, visible=False
        )
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

        @ttk.pyTTkSlot(int, int)
        def on_stats_resize(w, _h):

            if (w > 60):  # or self.stats_container.width() < (self.stats_container.height() * 2):
                set_orientation(ttk.TTkK.Direction.HORIZONTAL)
            else:
                set_orientation(ttk.TTkK.Direction.VERTICAL)

        def set_orientation(orientation: ttk.TTkK.Direction):

            if orientation == self.stats_container.orientation:
                return

            self.stats_container.layout().clear()

            if orientation == ttk.TTkK.Direction.HORIZONTAL:
                self.stats_container.setLayout(layout=ttk.TTkHBoxLayout())
                self.stats_container.orientation = ttk.TTkK.Direction.HORIZONTAL

            elif orientation == ttk.TTkK.Direction.VERTICAL:
                self.stats_container.setLayout(layout=ttk.TTkVBoxLayout())
                self.stats_container.orientation = ttk.TTkK.Direction.VERTICAL

            self.stats_container.layout().addWidgets([stats_box_a, stats_box_b])

        self.userinfo_container.sizeChanged.connect(on_resize)
        self.stats_container.sizeChanged.connect(on_stats_resize)

        self.user = user
        self.picture_bytes = None
        # self.picture_data = None
        # self.picture_surface = None
        # self.picture_extension = None
        self.indeterminate_progress = False
        self.refreshing = False

        self.populate_stats()
        self.update_button_states()

    def destroy(self):

        self.privileged_user_button.clicked.disconnect(self.on_privileged_user)
        self.send_message_button.clicked.disconnect(self.on_send_message)
        self.browse_files_button.clicked.disconnect(self.on_browse_user)
        self.add_remove_buddy_button.clicked.disconnect(self.on_add_remove_buddy)
        self.ban_unban_user_button.clicked.disconnect(self.on_ban_unban_user)
        self.ignore_unignore_user_button.clicked.disconnect(self.on_ignore_unignore_user)
        self.show_ip_address_button.clicked.disconnect(self.on_show_ip_address)
        self.refresh_button.clicked.disconnect(self.on_refresh)
        self.save_profile_button.clicked.disconnect(self.on_save_profile)

        self.userinfo_container.sizeChanged.clear()
        self.stats_container.sizeChanged.clear()

        self.save_picture_button.filePicked.disconnect(self.on_save_picture_response)
        self.select_picture_button.filePicked.disconnect(self.on_select_picture_response)
        self.save_picture_button.close()
        self.select_picture_button.close()

        self.clear()
        self.description_view.setLineWrapMode(ttk.TTkK.NoWrap)
        self.description_view.textEditView().viewMovedTo.clear()
        self.description_view.textEditView().viewSizeChanged.clear()
        self.description_view.textEditView().viewChanged.clear()
        self.description_view.document().cursorPositionChanged.clear()
        self.description_view.document().contentsChange.clear()
        self.description_view.document().contentsChanged.clear()
        self.description_view.document().formatChanged.clear()
        self.description_view.document().undoAvailable.clear()
        self.description_view.document().redoAvailable.clear()
        self.description_view.currentColorChanged.clear()
        self.description_view.cursorPositionChanged.clear()
        self.description_view.undoAvailable.clear()
        self.description_view.redoAvailable.clear()
        self.description_view.textChanged.clear()
        self.description_view.close()

        self.layout().clear()
        self.interests_picker.close()
        # self.close()

    def clear(self):
        self.description_view.setText("")
        self.description_view.setReadOnly(True)
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

    def pulse_progress(self):

        class Pl(ttk.TTkLookAndFeelFPBar):
            def color(self, _value, _maximum, _minimum):
                return ttk.TTkColor.fg("#000000") + ttk.TTkColor.bg("#FFAA40")

        class Pr(ttk.TTkLookAndFeelFPBar):
            def color(self, _value, _maximum, _minimum):
                return ttk.TTkColor.fg("#FFAA40") + ttk.TTkColor.bg("#000000")

        pulser_left = ttk.TTkFancyProgressBar(parent=self.progress_container, value=1, lookAndFeel=Pl(showText=False))
        pulser_right = ttk.TTkFancyProgressBar(parent=self.progress_container, lookAndFeel=Pr(showText=False))

        def pulse():
            if not self.indeterminate_progress:
                pulser_left.close()
                pulser_right.close()
                self.progress_bar.show()
                return

            if self.progress_bar.isVisible():
                self.progress_bar.hide()

            last_value = pulser_left.value()
            pulser_left.setValue(1 if not last_value else last_value - 0.05)
            pulser_right.setValue(1 - pulser_left.value())
            timer.start(0.1)  # repeat pulser

        timer = ttk.TTkTimer()
        timer.timeout.connect(pulse)
        timer.start(0.1)  # start pulser

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
        self.save_profile_button.setEnabled(False)

    # Button States #

    def update_local_buttons_state(self):

        is_editing_profile = (self.user == (core.users.login_username or config.sections["server"]["login"]))

        # (self.edit_interests_button, self.edit_profile_button):
        for widget in (self.select_picture_button, self.save_profile_button):
            widget.setVisible(is_editing_profile)

        for widget in (self.ban_unban_user_button, self.ignore_unignore_user_button,
                       self.gift_privileges_button, self.save_picture_button):
            widget.setVisible(not is_editing_profile)

        self.description_view.setReadOnly(not is_editing_profile)

        if not is_editing_profile:
            return

        self.description_frame.setTitle(_("Self Description"))
        self.description_view.setLineNumberStarting(1)
        self.description_view.setLineNumber(True)
        self.save_profile_button.setEnabled(False)

        @ttk.pyTTkSlot()
        def save():
            self.on_save_profile()

        @ttk.pyTTkSlot()
        def undo():
            self.description_view.setFocus()
            self.description_view.undo()  # FIXME: IndexError crash on undo past \n newline

        @ttk.pyTTkSlot()
        def redo():
            self.description_view.setFocus()
            self.description_view.redo()

        top_menu_bar = ttk.TTkMenuBarLayout()

        open_button = top_menu_bar.addMenu(" ⌂ ", alignment=ttk.TTkK.LEFT_ALIGN)  # 🯊
        open_button.setEnabled(False)
        open_button.setToolTip("Open")

        save_button = top_menu_bar.addMenu(" ↯ ", alignment=ttk.TTkK.LEFT_ALIGN)  # ≚
        save_button.setEnabled(False)
        save_button.setToolTip("Save")
        save_button.menuButtonClicked.connect(save)

        undo_button = top_menu_bar.addMenu(" ↶ ", alignment=ttk.TTkK.RIGHT_ALIGN)
        undo_button.setEnabled(False)
        undo_button.setToolTip("Undo")
        undo_button.menuButtonClicked.connect(undo)

        redo_button = top_menu_bar.addMenu(" ↷ ", alignment=ttk.TTkK.RIGHT_ALIGN)
        redo_button.setEnabled(False)
        redo_button.setToolTip("Redo")
        redo_button.menuButtonClicked.connect(redo)

        self.description_frame.setMenuBar(top_menu_bar, position=ttk.TTkK.TOP)

        @ttk.pyTTkSlot(bool)
        def enable_undo(is_available):
            undo_button.setEnabled(is_available)
            save_button.setEnabled(True)
            self.save_profile_button.setEnabled(True)

        self.description_view.document().undoAvailable.connect(enable_undo)
        self.description_view.document().redoAvailable.connect(redo_button.setEnabled)
        self.save_profile_button.clicked.connect(self.on_save_profile)

        def on_edit_interests():
            self.screen.tab_bar.setCurrentWidget(self.screen.interests)

        edit_menu_bar = ttk.TTkMenuBarLayout()
        edit_interests_button = edit_menu_bar.addMenu(" + ", alignment=ttk.TTkK.LEFT_ALIGN)  # ≓ _("Add…")
        edit_interests_button.setToolTip(_("Add Interests"))
        edit_interests_button.menuButtonClicked.connect(on_edit_interests)
        self.interests_picker.likes_list_container.setMenuBar(edit_menu_bar, position=ttk.TTkK.TOP)

    def update_buddy_button_state(self):
        label = _("Remove _Buddy") if self.user in core.buddies.users else _("Add _Buddy")
        self.add_remove_buddy_button.setText(label)
        # self.add_remove_buddy_label.set_text_with_mnemonic(label)

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
        # self.picture_data = None

        if self.select_picture_button.isVisible():
            # Editing local profile
            self.select_picture_button.setText(f'{_("Picture:")} {human_size(len(self.picture_bytes))}')
        else:
            self.save_picture_button.setEnabled(bool(self.picture_bytes))
            self.save_picture_button.setToolTip(human_size(len(self.picture_bytes)))

        self.info_bar.setVisible(False)
        self.set_finished()

    def user_status(self, msg=None):

        status_icon = USER_STATUS_ICONS.get(msg.status if msg else None)
        status_text = USER_STATUS_LABELS.get(msg.status if msg else None)

        self.user_status_label.setText(status_icon + ttk.TTkColor.RST + ttk.TTkColor.BOLD + status_text)
        self.privileged_user_button.setVisible(msg.privileged if msg else False)

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
        # log.add
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
        core.userinfo.save_user_picture(file_path, self.picture_bytes)

    @ttk.pyTTkSlot(str)
    def on_select_picture_response(self, file_path):

        self.select_picture_button.setPath(file_path)
        self.select_picture_button.setToolTip(file_path)

        if file_path != config.sections["userinfo"]["pic"]:
            self.select_picture_button.setText(f'{_("Picture:")} Changed')
            self.on_save_profile()

    def on_save_profile(self):

        from pynicotine.utils import unescape

        descr = repr(self.description_view.toPlainText())
        pic = self.select_picture_button.path()
        is_edited = False

        if unescape(descr) != unescape(config.sections["userinfo"]["descr"]):
            config.sections["userinfo"]["descr"] = descr
            is_edited = True

        if pic != config.sections["userinfo"]["pic"]:
            config.sections["userinfo"]["pic"] = pic
            is_edited = True

        if is_edited:
            config.write_configuration()

        self.description_view.setFocus()
        self.on_refresh()

    def on_refresh(self):
        core.userinfo.show_user(self.user, refresh=True)
