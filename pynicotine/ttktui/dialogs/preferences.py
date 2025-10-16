# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2016 Mutnick <muhing@yahoo.com>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2008 gallows <g4ll0ws@gmail.com>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-FileCopyrightText: 2003-2004 Nicotine Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
# from pynicotine.events import events
from pynicotine.shares import PermissionLevel
from pynicotine.ttktui.widgets.dialogs import Dialog
from pynicotine.ttktui.widgets.dialogs import EntryDialog
from pynicotine.ttktui.widgets.dialogs import OptionDialog
from pynicotine.ttktui.widgets.filechooser import FileChooserButton
from pynicotine.ttktui.widgets.options import Box
from pynicotine.ttktui.widgets.options import CheckBox
from pynicotine.ttktui.widgets.options import DropDownListBox
from pynicotine.ttktui.widgets.options import EntryBox
from pynicotine.ttktui.widgets.options import ListBox
from pynicotine.ttktui.widgets.options import SpinBox
from pynicotine.ttktui.widgets.theme import URL_COLOR_HEX
from pynicotine.utils import encode_path
from pynicotine.utils import open_folder_path


class DownloadsPage(ttk.TTkFrame):

    def __init__(self, application):
        super().__init__(border=False, layout=ttk.TTkHBoxLayout())  # title=_("Downloads"))  # name="downloads")

        self.application = application

        self.scroll_area = ttk.TTkScrollArea(parent=self)  # , horizontalScrollBarPolicy=ttk.TTkK.ScrollBarAlwaysOff)
        self.content_box = ttk.TTkContainer(parent=self.scroll_area.viewport(), layout=ttk.TTkVBoxLayout())

        self.create_page(self.content_box)

        self.sent_files_permission_combobox = DropDownListBox(
            container=self.sent_files_permission_container,
            items=[
                (_("No one"), 0),
                # "",
                (_("Buddies"), 2),
                (_("Trusted buddies"), 3)
            ]
        )

        items = [
            (_("Nothing"), 0)
        ]
        if not self.application.isolated_mode:
            items += [
                (_("Open File"), 1),
                (_("Open in File Manager"), 2)
            ]
        items += [
            (_("Search"), 3),
            (_("Pause"), 4),
            (_("Remove"), 5),
            (_("Resume"), 6),
            (_("Browse Folder"), 7)
        ]
        self.download_double_click_combobox = DropDownListBox(
            container=self.download_double_click_container,
            items=items
        )

        # self.filter_syntax_description = _("Syntax: Case-insensitive. If enabled, Python regular expressions "
        #                                    "can be used, otherwise only wildcard * matches are supported.")

        self.options = {
            "transfers": {
                "autoclear_downloads": self.autoclear_downloads_toggle,
                "remotedownloads": self.accept_sent_files_toggle,
                "uploadallowed": self.sent_files_permission_combobox,
                "incompletedir": self.incomplete_folder_button,
                "downloaddir": self.download_folder_button,
                "uploaddir": self.received_folder_button,
                # "enablefilters": self.enable_filters_toggle,
                # "downloadlimit": self.speed_spinner,
                # "downloadlimitalt": self.alt_speed_spinner,
                "usernamesubfolders": self.enable_username_subfolders_toggle,
                # "afterfinish": self.file_finished_command_entry,
                # "afterfolder": self.folder_finished_command_entry,
                "download_doubleclick": self.download_double_click_combobox
            }
        }

    def create_page(self, frame):

        group_containers = {}
        for group in [_("Downloads"), _("Download Speed Limits"), _("Folders"), _("Events"), _("Download Filters")]:
            group_container = group_containers[group] = ttk.TTkFrame(
                parent=frame, layout=ttk.TTkVBoxLayout(), title=group, titleAlign=ttk.TTkK.LEFT_ALIGN
            )
            group_container.layout().addWidget(ttk.TTkSpacer(minHeight=1))
            frame.layout().addWidget(ttk.TTkSpacer(minHeight=1))

        group_container = group_containers[_("Downloads")]
        self.autoclear_downloads_toggle = CheckBox(
            parent=group_container, text=_("Automatically remove finished and filtered downloads from list")
        )
        self.enable_username_subfolders_toggle = CheckBox(
            parent=group_container, text=_("Store completed downloads in username subfolders")
        )
        self.download_double_click_container = Box(
            parent=group_container, label_text=_("Double-click action for downloads:")
        )
        self.sent_files_permission_container = Box(parent=group_container)
        self.accept_sent_files_toggle = ttk.TTkCheckBox(
            parent=self.sent_files_permission_container, text=_("Allow users to send you any files:")
        )

        # group_container = group_containers[_("Download Speed Limits")]
        # self.recent_room_messages_spinner = SpinBox(
        #     parent=group_container, label_text=_("Number of recent chat room messages to show:"), maximum=10000
        # )

        group_container = group_containers[_("Folders")]
        self.download_folder_button = FileChooserButton(
            parent=group_container, label_text=_("Finished downloads:"),
            path=config.defaults["transfers"]["downloaddir"], fileMode=ttk.TTkK.FileMode.Directory,
            show_open_external_button=not self.application.isolated_mode
        )
        self.incomplete_folder_button = FileChooserButton(
            parent=group_container, label_text=_("Incomplete downloads:"),
            path=config.defaults["transfers"]["incompletedir"], fileMode=ttk.TTkK.FileMode.Directory,
            show_open_external_button=not self.application.isolated_mode
        )
        self.received_folder_button = FileChooserButton(
            parent=group_container, label_text=_("Received files:"),
            path=config.defaults["transfers"]["uploaddir"], fileMode=ttk.TTkK.FileMode.Directory,
            show_open_external_button=not self.application.isolated_mode
        )

        """
        (
            self.accept_sent_files_toggle,
            self.alt_speed_spinner,
            self.autoclear_downloads_toggle,
            self.container,
            self.download_double_click_label,
            self.download_folder_default_button,
            self.download_folder_label,
            self.enable_filters_toggle,
            self.enable_username_subfolders_toggle,
            self.file_finished_command_entry,
            self.filter_list_container,
            self.filter_status_label,
            self.folder_finished_command_entry,
            self.incomplete_folder_default_button,
            self.incomplete_folder_label,
            self.received_folder_default_button,
            self.received_folder_label,
            self.sent_files_permission_container,
            self.speed_spinner,
            self.use_alt_speed_limit_radio,
            self.use_speed_limit_radio,
            self.use_unlimited_speed_radio
        ) = self.widgets = ui.load(scope=self, path="settings/downloads.ui")
        """

        # self.scroll_area.viewport().viewChanged.emit()  # show scrollbar if needed
        # self.scroll_area.viewport().viewMoveTo(0, 0)

    def resizeEvent(self, w: int, h: int):
        self.content_box.setGeometry(
            0, 0,
            max(w - 1, self.content_box.minimumWidth()), self.content_box.minimumHeight() - 1
        )

    def destroy(self):

        # self.filter_popup_menu.destroy()
        self.download_folder_button.destroy()
        self.incomplete_folder_button.destroy()
        self.received_folder_button.destroy()
        # self.filter_list_view.destroy()

        self.__dict__.clear()

    def set_settings(self):

        # self.filter_list_view.clear()
        self.application.preferences.set_widgets_data(self.options)

        use_speed_limit = config.sections["transfers"]["use_download_speed_limit"]

        if use_speed_limit == "primary":
            pass  # self.use_speed_limit_radio.set_active(True)

        elif use_speed_limit == "alternative":
            pass  # self.use_alt_speed_limit_radio.set_active(True)

        else:
            pass  # self.use_unlimited_speed_radio.set_active(True)

        # self.filter_list_view.freeze()

        # for item in config.sections["transfers"]["downloadfilters"]:
        #     if not isinstance(item, list) or len(item) < 2:
        #         continue

        #     dfilter, escaped = item
        #     enable_regex = not escaped

        #     self.filter_list_view.add_row([dfilter, enable_regex], select_row=False)

        # self.filter_list_view.unfreeze()

    def get_settings(self):

        # if self.use_speed_limit_radio.get_active():
        #     use_speed_limit = "primary"

        # elif self.use_alt_speed_limit_radio.get_active():
        #     use_speed_limit = "alternative"

        # else:
        #     use_speed_limit = "unlimited"

        download_filters = []

        # for dfilter, iterator in self.filter_list_view.iterators.items():
        #     enable_regex = self.filter_list_view.get_row_value(iterator, "regex")
        #     download_filters.append([dfilter, not enable_regex])

        return {
            "transfers": {
                "autoclear_downloads": self.autoclear_downloads_toggle.get_active(),
                "remotedownloads": self.accept_sent_files_toggle.isChecked(),
                "uploadallowed": self.sent_files_permission_combobox.get_selected_id(),
                "incompletedir": self.incomplete_folder_button.get_path(),
                "downloaddir": self.download_folder_button.get_path(),
                "uploaddir": self.received_folder_button.get_path(),
                # "downloadfilters": download_filters,
                # "enablefilters": self.enable_filters_toggle.get_active(),
                # "use_download_speed_limit": use_speed_limit,
                # "downloadlimit": self.speed_spinner.get_value_as_int(),
                # "downloadlimitalt": self.alt_speed_spinner.get_value_as_int(),
                "usernamesubfolders": self.enable_username_subfolders_toggle.get_active(),
                # "afterfinish": self.file_finished_command_entry.get_text().strip(),
                # "afterfolder": self.folder_finished_command_entry.get_text().strip(),
                "download_doubleclick": self.download_double_click_combobox.get_selected_id()
            }
        }


class SharesPage(ttk.TTkFrame):

    PERMISSION_LEVELS = {
        _("Public"): PermissionLevel.PUBLIC,
        _("Buddies"): PermissionLevel.BUDDY,
        _("Trusted buddies"): PermissionLevel.TRUSTED
    }
    FILTER_LEVELS = {
        _("Applies to files"): _("Files"),
        _("Applies to folders"): _("Folders")
    }

    def __init__(self, application):
        super().__init__(layout=ttk.TTkHBoxLayout(), title=_("Shares"))  # name="shares")

        self.application = application

        # self.last_parent_folder = None
        self.shared_folders = []
        self.buddy_shared_folders = []
        self.trusted_shared_folders = []
        self.share_filters = []

        self._is_reveal_confirmed = False

        self.create_page(self)  # ttk.TTkFrame(parent=self, title=_("Shares")))

        self.options = {
            "transfers": {
                "rescanonstartup": self.rescan_on_startup_toggle,
                "rescan_shares_daily": self.rescan_daily_toggle,
                "rescan_shares_hour": self.rescan_hour_combobox,
                "reveal_buddy_shares": self.reveal_buddy_shares_toggle,
                "reveal_trusted_shares": self.reveal_trusted_shares_toggle
            }
        }

    def create_page(self, frame):

        shares_widgets_box = ttk.TTkContainer(
            parent=frame, layout=ttk.TTkVBoxLayout(),
            paddingTop=1, paddingBottom=0, paddingLeft=2, paddingRight=2
        )
        self.share_intro_text = ttk.TTkTextEdit(parent=shares_widgets_box, readOnly=True, maxHeight=4)
        self.share_intro_text.setLineWrapMode(ttk.TTkK.WidgetWidth)
        self.share_intro_text.setWordWrapMode(ttk.TTkK.WordWrap)
        self.share_intro_text.setText(
            _("Soulseek users will be able to download from your shares. Contribute to the Soulseek network "
              "by sharing your own files and by resharing what you downloaded from other users.")
        )

        rescan_container = ttk.TTkContainer(parent=shares_widgets_box, layout=ttk.TTkHBoxLayout(), paddingBottom=1)
        rescan_container.layout().addWidget(ttk.TTkLabel(text="Rescan shares:"))
        self.rescan_on_startup_toggle = ttk.TTkCheckbox(parent=rescan_container, text=_("On startup"))

        rescan_hour_container = ttk.TTkContainer(parent=rescan_container, layout=ttk.TTkHBoxLayout())
        self.rescan_daily_toggle = ttk.TTkCheckbox(parent=rescan_hour_container, text=_("Daily:"))
        self.rescan_hour_combobox = ttk.TTkComboBox(
            parent=rescan_hour_container, list=[f"{hour:02d}:00" for hour in range(24)], enabled=False
        )
        self.rescan_daily_toggle.toggled.connect(self.rescan_hour_combobox.setEnabled)

        # reveal_container = ttk.TTkContainer(parent=shares_widgets_box, layout=ttk.TTkHBoxLayout(), paddingBottom=1)
        # reveal_container.layout().addWidget(ttk.TTkLabel(text="Reveal private shares:"))  # new string
        # reveal_container.layout().addWidget(ttk.TTkSpacer())
        # self.reveal_buddy_shares_toggle = ttk.TTkCheckbox(parent=reveal_container, text=_("Buddy shares"))
        # self.reveal_trusted_shares_toggle = ttk.TTkCheckbox(parent=reveal_container, text=_("Trusted shares"))

        self.tab_bar = ttk.TTkTabWidget(parent=shares_widgets_box, closable=False, movable=False)  # setTabsMovable()
        self.tab_bar.currentChanged.connect(self.tab_bar.clearFocus)

        reveal_private_menu = self.tab_bar.addMenu(_("Private"), position=ttk.TTkK.RIGHT)
        self.reveal_buddy_shares_toggle = reveal_private_menu.addMenu("Reveal buddy shares", checkable=True)
        self.reveal_buddy_shares_toggle.toggled.connect(self.on_reveal_buddy_shares_toggled)
        self.reveal_trusted_shares_toggle = reveal_private_menu.addMenu("Reveal trusted shares", checkable=True)
        self.reveal_trusted_shares_toggle.toggled.connect(self.on_reveal_trusted_shares_toggled)

        self._refresh_shares_list_button = self.tab_bar.addMenu(" ↻ ", position=ttk.TTkK.LEFT)
        self._refresh_shares_list_button.setToolTip("Refresh Shares List")
        self._refresh_shares_list_button.menuButtonClicked.connect(self.on_refresh_shares_list)

        # Shared Folders
        shares_list_container = ttk.TTkContainer(layout=ttk.TTkVBoxLayout())  # , paddingBottom=-1)
        self.shares_list_view = ttk.TTkTree(
            parent=shares_list_container, header=[" ", _("Folder"), _("Virtual Folder"), _("Accessible To")],
            selectionMode=ttk.TTkK.SelectionMode.MultiSelection, name="shares_list", minHeight=3
        )
        self.shares_list_view.itemClicked.connect(self.on_shared_folder_clicked)
        self.shares_list_view.itemActivated.connect(self.on_shared_folder_activated)

        for col, width in enumerate([3, 24, 18, 15]):
            self.shares_list_view.setColumnWidth(col, width)

        shares_buttons_box = ttk.TTkContainer(
            parent=shares_list_container, layout=ttk.TTkHBoxLayout(), paddingLeft=1, paddingRight=1, maxHeight=1
        )
        self._add_shared_folder_button = ttk.TTkFileButtonPicker(
            parent=shares_buttons_box, text=_("Add…"), caption=_("Select a Folder") + " to Share",
            fileMode=ttk.TTkK.FileMode.Directory, filter=f"Folders (*{os.sep});;All Files (*)"
        )
        self._add_shared_folder_button.folderPicked.connect(self.on_add_shared_folder_selected)

        self._edit_shared_folder_button = ttk.TTkButton(parent=shares_buttons_box, text=_("Edit…"), enabled=False)
        self._edit_shared_folder_button.clicked.connect(self.on_edit_shared_folder)

        self._remove_shared_folder_button = ttk.TTkButton(parent=shares_buttons_box, text=_("Remove"), enabled=False)
        self._remove_shared_folder_button.clicked.connect(self.on_remove_shared_folder)

        shares_buttons_box.layout().addWidget(ttk.TTkSpacer())
        shares_buttons_box.layout().addWidget(ttk.TTkSpacer())

        # self.shares_count_label = ttk.TTkLabel(
        #     parent=shares_buttons_box, text="Listing shares…", alignment=ttk.TTkK.CENTER_ALIGN,
        # )
        # self.shares_list_view._treeView.viewSizeChanged.connect(self.on_shares_list_changed)

        self.file_manager_button = ttk.TTkButton(parent=shares_buttons_box, text=_("File _Manager"), enabled=False)
        self.file_manager_button.setVisible(not self.application.isolated_mode)
        self.file_manager_button.clicked.connect(self.on_open_file_manager)

        # Filters
        filter_list_container = ttk.TTkContainer(layout=ttk.TTkVBoxLayout())  # , paddingBottom=-1)
        self.filter_list_view = ttk.TTkTree(
            parent=filter_list_container, header=[" ", _("Filter"), _("Applies To")],
            selectionMode=ttk.TTkK.SelectionMode.MultiSelection, name="filter_list", minHeight=3
        )
        self.filter_list_view.itemClicked.connect(self.on_filter_clicked)
        self.filter_list_view.itemActivated.connect(self.on_filter_activated)

        for col, width in enumerate([3, 44, 15]):
            self.filter_list_view.setColumnWidth(col, width)

        filter_buttons_box = ttk.TTkContainer(
            parent=filter_list_container, layout=ttk.TTkHBoxLayout(), paddingLeft=1, paddingRight=1, maxHeight=1
        )
        self._add_filter_button = ttk.TTkButton(parent=filter_buttons_box, text=_("Add…"))
        self._add_filter_button.clicked.connect(self.on_add_filter)

        self._edit_filter_button = ttk.TTkButton(parent=filter_buttons_box, text=_("Edit…"), enabled=False)
        self._edit_filter_button.clicked.connect(self.on_edit_filter)

        self._remove_filter_button = ttk.TTkButton(parent=filter_buttons_box, text=_("Remove"), enabled=False)
        self._remove_filter_button.clicked.connect(self.on_remove_filter)

        filter_buttons_box.layout().addWidget(ttk.TTkSpacer())
        filter_buttons_box.layout().addWidget(ttk.TTkSpacer())

        self._default_filters_button = ttk.TTkButton(parent=filter_buttons_box, text="↺", maxWidth=5, enabled=False)
        self._default_filters_button.setToolTip(_("Load Defaults"))
        self._default_filters_button.clicked.connect(self.on_default_filters)

        self.filter_list_view._treeView.viewSizeChanged.connect(self.on_filter_list_changed)

        self.filter_syntax_description = _("Syntax: Case-insensitive. Virtual paths containing separators \\ are "
                                           "supported. Wildcard * matches are supported.")
        len_title = 0
        for widget, title in (
            (shares_list_container, _("Shared Folders")),
            (filter_list_container, _("Filters"))
        ):
            len_title = max(len_title, len(title))
            self.tab_bar.addTab(widget, title.center(len_title+2))

        self.shares_info_bar = ttk.TTkLabel(parent=shares_widgets_box, alignment=ttk.TTkK.CENTER_ALIGN, maxHeight=1)

    def destroy(self):

        # for menu in self.popup_menus:
        #     menu.destroy()

        self.shares_list_view.close()
        self.filter_list_view.close()

        self.__dict__.clear()

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)

        self.shared_folders = config.sections["transfers"]["shared"][:]
        self.buddy_shared_folders = config.sections["transfers"]["buddyshared"][:]
        self.trusted_shared_folders = config.sections["transfers"]["trustedshared"][:]
        self.share_filters = config.sections["transfers"]["share_filters"][:]

        self.filter_list_view.clear()
        self.filter_list_view._treeView.setSortingEnabled(False)

        for sfilter in self.share_filters:
            applies_to = _("Folders") if sfilter.endswith("\\") else _("Files")
            self.filter_list_view.addTopLevelItem(ttk.TTkTreeWidgetItem(["", sfilter, applies_to]))

        self.filter_list_view._treeView.setSortingEnabled(True)
        self.filter_list_view.sortItems(1, ttk.TTkK.AscendingOrder)  # Filter

        self._list_shares()

    def get_settings(self):

        return {
            "transfers": {
                "shared": self.shared_folders[:],
                "buddyshared": self.buddy_shared_folders[:],
                "trustedshared": self.trusted_shared_folders[:],
                "share_filters": self.share_filters[:],
                "rescanonstartup": self.rescan_on_startup_toggle.isChecked(),
                "rescan_shares_daily": self.rescan_daily_toggle.isChecked(),
                "rescan_shares_hour": self.rescan_hour_combobox.currentIndex(),  # currentText.rstrip(":00")
                "reveal_buddy_shares": self.reveal_buddy_shares_toggle.isChecked(),
                "reveal_trusted_shares": self.reveal_trusted_shares_toggle.isChecked()
            }
        }

    @ttk.pyTTkSlot(int)
    def on_switch_tab(self, tab_number):
        self.filter_list_view.setFocus() if tab_number == 1 else self.shares_list_view.setFocus()

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_shared_folder_clicked(self, _share_item, _col):
        is_selections = bool(self.shares_list_view.selectedItems())
        self._edit_shared_folder_button.setEnabled(is_selections)
        self._remove_shared_folder_button.setEnabled(is_selections)
        self.file_manager_button.setEnabled(is_selections)

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_shared_folder_activated(self, _share_item, _col):
        self.on_edit_shared_folder()

    # @ttk.pyTTkSlot()
    # def on_shares_list_changed(self):
    #     self.shares_count_label.setText("%i shared folders" % self.shares_list_view.invisibleRootItem().size())

    @ttk.pyTTkSlot()
    def on_refresh_shares_list(self):
        self._list_shares()
        self.shares_list_view.setFocus()

    def _list_shares(self):

        self.shares_list_view.clear()
        self.shares_list_view._treeView.setSortingEnabled(False)

        unreadable_shares = core.shares.check_shares_available()

        for virtual_name, folder_path, *_unused in self.shared_folders:
            self._add_share_item(virtual_name, folder_path, _("Public"), unreadable_shares=unreadable_shares)

        for virtual_name, folder_path, *_unused in self.buddy_shared_folders:
            self._add_share_item(virtual_name, folder_path, _("Buddies"), unreadable_shares=unreadable_shares)

        for virtual_name, folder_path, *_unused in self.trusted_shared_folders:
            self._add_share_item(virtual_name, folder_path, _("Trusted"), unreadable_shares=unreadable_shares)

        self.shares_list_view._treeView.setSortingEnabled(True)
        self.shares_list_view.sortItems(2, ttk.TTkK.AscendingOrder)  # Virtual Folder

        if unreadable_shares:
            self.shares_info_bar.setText(f'{len(unreadable_shares)} {_("Shares Not Available")}')
            self.shares_info_bar.setColor(ttk.TTkColor.BOLD + ttk.TTkColor.BG_RED)
        else:
            self.shares_info_bar.setText("")
            self.shares_info_bar.setColor(ttk.TTkColor.RST)

        self.tab_bar.setCurrentIndex(0)

    def _add_share_item(self, virtual_name, folder_path, permission_level, unreadable_shares=None):

        if unreadable_shares is None:
            unreadable_shares = core.shares.check_shares_available()

        if (virtual_name, folder_path) in unreadable_shares:
            icon = ttk.TTkString(" 🛇 ", ttk.TTkColor.BOLD + ttk.TTkColor.RED + ttk.TTkColor.BLINKING)
            icon_label = _("Unreadable")
        else:
            icon = ""
            icon_label = ""
            self._add_shared_folder_button.setPath(os.path.dirname(folder_path.rstrip(os.sep)))

        share_item = ttk.TTkTreeWidgetItem([icon_label, folder_path, virtual_name, permission_level])
        share_item.setIcon(0, icon)

        self.shares_list_view.addTopLevelItem(share_item)
        return share_item

    @ttk.pyTTkSlot(str)
    def on_add_shared_folder_selected(self, folder_path):

        virtual_name = core.shares.add_share(
            folder_path, share_groups=(self.shared_folders, self.buddy_shared_folders, self.trusted_shared_folders)
        )

        if not virtual_name:
            basename = folder_path.rstrip(os.sep).rpartition(os.sep)[-1] or folder_path
            self.shares_info_bar.setText(
                ttk.TTkString(_("Cannot share inaccessible folder \"%s\"") % basename, ttk.TTkColor.BG_RED)
            )
            return

        # self.last_parent_folder = os.path.dirname(folder_path)
        self._add_share_item(virtual_name, folder_path, _("Public"))

        self.shares_info_bar.setText(
            _("Added %(group_name)s share \"%(virtual_name)s\" (rescan required)") % {
                "group_name": "public",
                "virtual_name": virtual_name
            }
        )
        self.shares_info_bar.setColor(ttk.TTkColor.GREEN)
        # self.rescan_required = True

    @ttk.pyTTkSlot()
    def on_edit_shared_folder(self):

        def response(dialog, _response_button, old_share_item):

            new_virtual_name = dialog.get_entry_value()
            new_group_name = dialog.get_second_entry_value()
            new_group_name_short = new_group_name.replace(_("Trusted buddies"), _("Trusted"))

            if new_virtual_name == old_virtual_name and new_group_name_short == old_group_name:
                return

            core.shares.remove_share(
                old_virtual_name,
                share_groups=(self.shared_folders, self.buddy_shared_folders, self.trusted_shared_folders)
            )
            # self.shares_list_view.invisibleRootItem().removeChild(old_share_item)
            old_share_item.setHidden(True)  # workaround to remove item
            # self.rescan_required = True

            permission_level = self.PERMISSION_LEVELS.get(new_group_name)
            new_virtual_name = core.shares.add_share(
                folder_path,
                permission_level=permission_level,
                virtual_name=new_virtual_name,
                share_groups=(self.shared_folders, self.buddy_shared_folders, self.trusted_shared_folders),
                validate_path=False
            )
            new_share_item = self._add_share_item(
                new_virtual_name,
                folder_path,
                new_group_name_short
            )
            self.shares_info_bar.setText(
                _("Added %(group_name)s share \"%(virtual_name)s\" (rescan required)") % {
                    "group_name": new_group_name_short.lower(),
                    "virtual_name": new_virtual_name
                }
            )
            self.shares_info_bar.setColor(ttk.TTkColor.GREEN)

        for share_item in self.shares_list_view.selectedItems():
            if share_item.isHidden():
                # Already removed workaround
                continue

            folder_path = str(share_item.data(1))
            old_virtual_name = str(share_item.data(2))
            old_group_name = str(share_item.data(3))

            EntryDialog(
                parent=self.application.preferences.window,
                title=_("Edit Shared Folder"),
                message=_("Enter new virtual name for '%(dir)s':") % {"dir": folder_path},
                default=old_virtual_name,
                second_default=old_group_name.replace(_("Trusted"), _("Trusted buddies")),
                second_droplist=list(self.PERMISSION_LEVELS),
                use_second_entry=True,
                second_entry_editable=False,
                action_button_label=_("_Edit"),
                callback=response,
                callback_data=share_item
            ).present()
            return

        self._edit_shared_folder_button.setEnabled(False)  # bool(self.shares_list_view.selectedItems()))

    @ttk.pyTTkSlot()
    def on_remove_shared_folder(self):

        for share_item in reversed(self.shares_list_view.selectedItems()):
            if share_item.isHidden():
                # Already removed workaround
                continue

            virtual_name = str(share_item.data(2))

            core.shares.remove_share(
                virtual_name, share_groups=(self.shared_folders, self.buddy_shared_folders, self.trusted_shared_folders)
            )
            # self.shares_list_view.invisibleRootItem().removeChild(share_item)
            share_item.setHidden(True)  # workaround to remove item
            # self.rescan_required = True

            self.shares_info_bar.setText(_("Removed share \"%s\" (rescan required)") % virtual_name)
            self.shares_info_bar.setColor(ttk.TTkColor.GREEN)

        self._remove_shared_folder_button.setEnabled(False)  # bool(self.shares_list_view.selectedItems()))

    @ttk.pyTTkSlot()
    def on_open_file_manager(self):
        for share_item in self.shares_list_view.selectedItems():
            folder_path = str(share_item.data(1))
            open_folder_path(folder_path, create_folder=True)
            return

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_filter_clicked(self, _filter_item, _col):
        is_selections = bool(self.filter_list_view.selectedItems())
        self._edit_filter_button.setEnabled(is_selections)
        self._remove_filter_button.setEnabled(is_selections)

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_filter_activated(self, _filter_item, _col):
        self.on_edit_filter()

    @ttk.pyTTkSlot()
    def on_filter_list_changed(self):
        self._default_filters_button.setEnabled(self.share_filters != config.defaults["transfers"]["share_filters"])

    def process_filter(self, sfilter, applies_to):

        sfilter = sfilter.replace("/", "\\").rstrip("\\")

        if applies_to == _("Folders"):
            suffix = "\\*"
            if sfilter.endswith(suffix):
                sfilter = sfilter[:-len(suffix)]
            sfilter += "\\"

        return sfilter

    @ttk.pyTTkSlot()
    def on_add_filter(self):

        def response(dialog, _response_button, _data):

            sfilter = dialog.get_entry_value()
            applies_to = self.FILTER_LEVELS[dialog.get_second_entry_value()]
            sfilter = self.process_filter(sfilter, applies_to)

            if sfilter in self.share_filters:
                self.shares_info_bar.setText("Duplicate %s share filter \"%s\"" % (applies_to.lower(), sfilter))
                self.shares_info_bar.setColor(ttk.TTkColor.BOLD + ttk.TTkColor.BG_RED)
                return

            self.share_filters.append(sfilter)
            self.filter_list_view.addTopLevelItem(ttk.TTkTreeWidgetItem(["", sfilter, applies_to]))

        EntryDialog(
            parent=self.application.preferences.window,
            icon=EntryDialog.Icon.Information,
            title=_("Add Share Filter"),
            message=_("Enter a new share filter:"),
            long_message=self.filter_syntax_description,
            second_droplist=list(self.FILTER_LEVELS),
            use_second_entry=True,
            second_entry_editable=False,
            action_button_label=_("_Add"),
            callback=response,
            # droplist=self.filter_list_view.iterators
        ).present()

    @ttk.pyTTkSlot()
    def on_edit_filter(self):

        def response(dialog, _response_button, old_filter_item):

            new_sfilter = dialog.get_entry_value()
            new_applies_to = self.FILTER_LEVELS[dialog.get_second_entry_value()]
            new_sfilter = self.process_filter(new_sfilter, new_applies_to)

            self.share_filters.remove(old_sfilter)
            old_filter_item.setHidden(True)
            # self.filter_list_view.remove_row(old_filter_item)

            self.share_filters.append(new_sfilter)
            self.filter_list_view.addTopLevelItem(ttk.TTkTreeWidgetItem(["", new_sfilter, new_applies_to]))

        for filter_item in self.filter_list_view.selectedItems():
            if filter_item.isHidden():
                # Already removed workaround
                continue

            old_sfilter = str(filter_item.data(1))
            old_applies_to = str(filter_item.data(2))

            EntryDialog(
                parent=self.application.preferences.window,
                icon=EntryDialog.Icon.Information,
                title=_("Edit Share Filter"),
                message=_("Modify the following share filter:"),
                long_message=self.filter_syntax_description,
                default=old_sfilter,
                second_default={v: k for k, v in self.FILTER_LEVELS.items()}[old_applies_to],
                second_droplist=list(self.FILTER_LEVELS),
                use_second_entry=True,
                second_entry_editable=False,
                action_button_label=_("_Edit"),
                callback=response,
                callback_data=filter_item
            ).present()
            return

        self._edit_filter_button.setEnabled(False)  # bool(self.filter_list_view.selectedItems()))

    @ttk.pyTTkSlot()
    def on_remove_filter(self):

        for filter_item in reversed(self.filter_list_view.selectedItems()):
            if filter_item.isHidden():
                # Already removed workaround
                continue

            sfilter = str(filter_item.data(1))

            self.share_filters.remove(sfilter)
            filter_item.setHidden(True)

        self._remove_filter_button.setEnabled(False)  # bool(self.filter_list_view.selectedItems())

    @ttk.pyTTkSlot()
    def on_default_filters(self):

        self.share_filters.clear()
        self.filter_list_view.clear()
        self.filter_list_view._treeView.setSortingEnabled(False)

        self.share_filters = config.defaults["transfers"]["share_filters"][:]

        for sfilter in config.defaults["transfers"]["share_filters"]:
            applies_to = _("Folders") if sfilter.endswith("\\") else _("Files")
            self.filter_list_view.addTopLevelItem(ttk.TTkTreeWidgetItem(["", sfilter, applies_to]))

        self.filter_list_view._treeView.setSortingEnabled(True)

    @ttk.pyTTkSlot(bool)
    def on_reveal_buddy_shares_toggled(self, enabled):
        if enabled and not self._is_reveal_confirmed:
            self._reveal_confirmation(self.reveal_buddy_shares_toggle)
        self.tab_bar.clearFocus()

    @ttk.pyTTkSlot(bool)
    def on_reveal_trusted_shares_toggled(self, enabled):
        if enabled and not self._is_reveal_confirmed:
            self._reveal_confirmation(self.reveal_trusted_shares_toggle)
        self.tab_bar.clearFocus()

    def _reveal_confirmation(self, toggle_widget):

        toggle_widget.setChecked(False)

        def response(dialog, button, _data):

            if button == OptionDialog.StandardButton.RestoreDefaults:
                self.reveal_buddy_shares_toggle.setChecked(False)
                self.reveal_trusted_shares_toggle.setChecked(False)

            elif dialog.get_option_value() and button == OptionDialog.StandardButton.Yes:
                self._is_reveal_confirmed = True
                toggle_widget.setChecked(True)

            self._is_reveal_confirmed = False
            self.tab_bar.clearFocus()

        if toggle_widget == self.reveal_buddy_shares_toggle:
            title = "Reveal Private Buddy Shares to Everyone"
        else:
            title = "Reveal Private Trusted Buddy Shares to Everyone"

        OptionDialog(
            parent=self.application.screen,  # preferences.window,
            icon=OptionDialog.Icon.Warning,
            title=title,
            message="Are you sure you want to reveal private buddy shares?",
            long_message=(
                "Users are prevented from downloading private files unless they are a buddy." + "\n\n"
                "If you want to share files with everyone then make folders available in your public shares instead of"
                " revealing private shares."
            ),
            buttons=[
                (OptionDialog.StandardButton.RestoreDefaults, "Restore Defaults"),
                (OptionDialog.StandardButton.Yes, "Confirm")
            ],
            default_button=OptionDialog.StandardButton.RestoreDefaults,
            destructive_button=OptionDialog.StandardButton.Yes,
            option_label=f"{title} (not recommended)",
            callback=response
        ).present()


class UploadsPage(ttk.TTkFrame):

    def __init__(self, application):
        super().__init__(border=False, layout=ttk.TTkHBoxLayout())

        self.application = application

        self.scroll_area = ttk.TTkScrollArea(parent=self)  # , horizontalScrollBarPolicy=ttk.TTkK.ScrollBarAlwaysOff)
        self.content_box = ttk.TTkContainer(parent=self.scroll_area.viewport(), layout=ttk.TTkVBoxLayout())

        self.create_page(self.content_box)

        items = [
            (_("Nothing"), 0)
        ]
        if not self.application.isolated_mode:
            items += [
                (_("Open File"), 1),
                (_("Open in File Manager"), 2)
            ]
        items += [
            (_("Search"), 3),
            (_("Abort"), 4),
            (_("Remove"), 5),
            (_("Retry"), 6),
            (_("Browse Folder"), 7)
        ]
        self.upload_double_click_combobox = DropDownListBox(
            container=self.upload_double_click_container,
            items=items
        )

        # self.upload_queue_type_combobox = ComboBox(
        #     container=self.upload_queue_type_label.get_parent(), label=self.upload_queue_type_label,
        #     items=(
        #         (_("Round Robin"), 0),
        #         (_("First In, First Out"), 1)
        #     )
        # )

        self.options = {
            "transfers": {
                "autoclear_uploads": self.autoclear_uploads_toggle,
                # "uploadbandwidth": self.upload_bandwidth_spinner,
                # "useupslots": self.use_upload_slots_fixed_radio,
                # "uploadslots": self.upload_slots_spinner,
                # "uploadlimit": self.speed_spinner,
                # "uploadlimitalt": self.alt_speed_spinner,
                # "fifoqueue": self.upload_queue_type_combobox,
                # "limitby": self.limit_total_transfers_radio,
                # "queuelimit": self.max_queued_size_spinner,
                # "filelimit": self.max_queued_files_spinner,
                # "friendsnolimits": self.no_buddy_limits_toggle,
                # "preferfriends": self.prioritize_buddies_toggle,
                "upload_doubleclick": self.upload_double_click_combobox
            }
        }

    def create_page(self, frame):

        group_containers = {}
        for group in [_("Uploads"), _("Upload Speed Limits"), _("Upload Slots"), _("Queue Limits")]:
            group_container = group_containers[group] = ttk.TTkFrame(
                parent=frame, layout=ttk.TTkVBoxLayout(), title=group, titleAlign=ttk.TTkK.LEFT_ALIGN
            )
            group_container.layout().addWidget(ttk.TTkSpacer(minHeight=1))
            frame.layout().addWidget(ttk.TTkSpacer(minHeight=1))

        group_container = group_containers[_("Uploads")]
        self.autoclear_uploads_toggle = CheckBox(
            parent=group_container, text=_("Automatically remove finished and cancelled uploads from list")
        )
        self.upload_double_click_container = Box(
            parent=group_container, label_text=_("Double-click action for uploads:")
        )

        # group_container = group_containers[_("Upload Speed Limits")]

        """
        (
            self.alt_speed_spinner,
            self.autoclear_uploads_toggle,
            self.container,
            self.limit_total_transfers_radio,
            self.max_queued_files_spinner,
            self.max_queued_size_spinner,
            self.no_buddy_limits_toggle,
            self.prioritize_buddies_toggle,
            self.speed_spinner,
            self.upload_bandwidth_spinner,
            self.upload_double_click_label,
            self.upload_queue_type_label,
            self.upload_slots_spinner,
            self.use_alt_speed_limit_radio,
            self.use_speed_limit_radio,
            self.use_unlimited_speed_radio,
            self.use_upload_slots_bandwidth_radio,
            self.use_upload_slots_fixed_radio
        ) = self.widgets = ui.load(scope=self, path="settings/uploads.ui")
        """

    def resizeEvent(self, w: int, h: int):
        self.content_box.setGeometry(
            0, 0,
            max(w - 1, self.content_box.minimumWidth()), self.content_box.minimumHeight() - 1
        )

    def destroy(self):

        # self.upload_double_click_combobox.destroy()
        # self.upload_queue_type_combobox.destroy()

        self.__dict__.clear()

    def set_settings(self):

        self.application.preferences.set_widgets_data(self.options)

        use_speed_limit = config.sections["transfers"]["use_upload_speed_limit"]

        # if use_speed_limit == "primary":
        #     self.use_speed_limit_radio.set_active(True)

        # elif use_speed_limit == "alternative":
        #     self.use_alt_speed_limit_radio.set_active(True)

        # else:
        #     self.use_unlimited_speed_radio.set_active(True)

    def get_settings(self):

        # if self.use_speed_limit_radio.get_active():
        #     use_speed_limit = "primary"

        # elif self.use_alt_speed_limit_radio.get_active():
        #     use_speed_limit = "alternative"

        # else:
        #     use_speed_limit = "unlimited"

        return {
            "transfers": {
                "autoclear_uploads": self.autoclear_uploads_toggle.get_active(),
                # "uploadbandwidth": self.upload_bandwidth_spinner.get_value_as_int(),
                # "useupslots": self.use_upload_slots_fixed_radio.get_active(),
                # "uploadslots": self.upload_slots_spinner.get_value_as_int(),
                # "use_upload_speed_limit": use_speed_limit,
                # "uploadlimit": self.speed_spinner.get_value_as_int(),
                # "uploadlimitalt": self.alt_speed_spinner.get_value_as_int(),
                # "fifoqueue": bool(self.upload_queue_type_combobox.get_selected_id()),
                # "limitby": self.limit_total_transfers_radio.get_active(),
                # "queuelimit": self.max_queued_size_spinner.get_value_as_int(),
                # "filelimit": self.max_queued_files_spinner.get_value_as_int(),
                # "friendsnolimits": self.no_buddy_limits_toggle.get_active(),
                # "preferfriends": self.prioritize_buddies_toggle.get_active(),
                "upload_doubleclick": self.upload_double_click_combobox.get_selected_id()
            }
        }


class ChatsPage(ttk.TTkFrame):

    def __init__(self, application):
        super().__init__(border=False, layout=ttk.TTkHBoxLayout())

        self.application = application

        self.scroll_area = ttk.TTkScrollArea(parent=self)  # , horizontalScrollBarPolicy=ttk.TTkK.ScrollBarAlwaysOff)
        self.content_box = ttk.TTkContainer(parent=self.scroll_area.viewport(), layout=ttk.TTkVBoxLayout())

        self.create_page(self.content_box)

        self.options = {
            "server": {
                "ctcpmsgs": None,  # Special case in set_settings
                "private_chatrooms": self.room_invitations_toggle
            },
            "logging": {
                "readroomlines": self.recent_room_messages_spinner,
                "readprivatelines": self.recent_private_messages_spinner,
                "rooms_timestamp": self.timestamp_room_entry,
                "private_timestamp": self.timestamp_private_chat_entry
            },
            "privatechat": {
                "store": self.reopen_private_chats_toggle
            },
            "words": {
                # "tab": self.enable_tab_completion_toggle,
                # "dropdown": self.enable_completion_dropdown_toggle,
                # "characters": self.min_chars_dropdown_spinner,
                # "roomnames": self.complete_room_names_toggle,
                # "buddies": self.complete_buddy_names_toggle,
                # "roomusers": self.complete_room_usernames_toggle,
                # "commands": self.complete_commands_toggle,
                # "censored": self.censor_list_view,
                # "censorwords": self.censor_text_patterns_toggle,
                # "autoreplaced": self.replacement_list_view,
                # "replacewords": self.auto_replace_words_toggle
            },
            "ui": {
                # "spellcheck": self.enable_spell_checker_toggle
            }
        }

    def create_page(self, frame):

        group_containers = {}
        for group in [_("Chats"), _("Chat Completion"), _("Timestamps")]:
            group_container = group_containers[group] = ttk.TTkFrame(
                parent=frame, layout=ttk.TTkVBoxLayout(), title=group, titleAlign=ttk.TTkK.LEFT_ALIGN
            )
            group_container.layout().addWidget(ttk.TTkSpacer(minHeight=1))
            frame.layout().addWidget(ttk.TTkSpacer(minHeight=1))

        group_container = group_containers[_("Chats")]
        self.room_invitations_toggle = CheckBox(
            parent=group_container, text=_("Accept private room invitations")
        )
        self.reopen_private_chats_toggle = CheckBox(
            parent=group_container, text=_("Restore previously open private chats on startup")
        )
        # self.enable_spell_checker_toggle = ttk.TTkCheckbox(parent=chats_group, label_text=_("Enable spell checker"))
        self.enable_ctcp_toggle = CheckBox(
            parent=group_container, text="Enable CTCP-like private message responses"  # (client version)"
        )
        self.recent_private_messages_spinner = SpinBox(
            parent=group_container, label_text=_("Number of recent private chat messages to show:"), maximum=10000
        )
        self.recent_room_messages_spinner = SpinBox(
            parent=group_container, label_text=_("Number of recent chat room messages to show:"), maximum=10000
        )

        # group_container = group_containers[_("Chat Completion")]

        group_container = group_containers[_("Timestamps")]
        self.timestamp_private_chat_entry = EntryBox(parent=group_container, label_text=_("Private chat format:"))
        self.timestamp_room_entry = EntryBox(parent=group_container, label_text=_("Chat room format:"))
        format_codes_box = ttk.TTkContainer(parent=group_container, layout=ttk.TTkHBoxLayout(), padding=(0, 0, 0, 1))
        self.format_codes_label = ttk.TTkLabel(
            parent=format_codes_box,
            alignment=ttk.TTkK.RIGHT_ALIGN,
            text=ttk.TTkString(
                ("Format codes"),
                ttk.TTkColor.fg(URL_COLOR_HEX, link="https://docs.python.org/3/library/datetime.html#format-codes")
            )
        )

    def resizeEvent(self, w: int, h: int):
        self.content_box.setGeometry(
            0, 0,
            max(w - 1, self.content_box.minimumWidth()), self.content_box.minimumHeight() - 1
        )

    def destroy(self):

        # for menu in self.popup_menus:
        #     menu.destroy()

        # self.censor_list_view.destroy()
        # self.replacement_list_view.destroy()

        self.__dict__.clear()

    def set_settings(self):

        # self.censor_list_view.clear()
        # self.replacement_list_view.clear()
        # self.censored_patterns.clear()
        # self.replacements.clear()

        self.application.preferences.set_widgets_data(self.options)

        # self.enable_spell_checker_toggle.get_parent().set_visible(SpellChecker.is_available())
        self.enable_ctcp_toggle.setChecked(not config.sections["server"]["ctcpmsgs"])
        # self.format_codes_label.set_visible(not self.application.isolated_mode)

        # self.censored_patterns = config.sections["words"]["censored"][:]
        # self.replacements = config.sections["words"]["autoreplaced"].copy()

    def get_settings(self):

        return {
            "server": {
                "ctcpmsgs": not self.enable_ctcp_toggle.get_active(),
                "private_chatrooms": self.room_invitations_toggle.get_active()
            },
            "logging": {
                "readroomlines": self.recent_room_messages_spinner.get_value_as_int(),
                "readprivatelines": self.recent_private_messages_spinner.get_value_as_int(),
                "private_timestamp": self.timestamp_private_chat_entry.get_text(),
                "rooms_timestamp": self.timestamp_room_entry.get_text()
            },
            "privatechat": {
                "store": self.reopen_private_chats_toggle.get_active()
            },
            "words": {
                # "tab": self.enable_tab_completion_toggle.get_active(),
                # "dropdown": self.enable_completion_dropdown_toggle.get_active(),
                # "characters": self.min_chars_dropdown_spinner.get_value_as_int(),
                # "roomnames": self.complete_room_names_toggle.get_active(),
                # "buddies": self.complete_buddy_names_toggle.get_active(),
                # "roomusers": self.complete_room_usernames_toggle.get_active(),
                # "commands": self.complete_commands_toggle.get_active(),
                # "censored": self.censored_patterns[:],
                # "censorwords": self.censor_text_patterns_toggle.get_active(),
                # "autoreplaced": self.replacements.copy(),
                # "replacewords": self.auto_replace_words_toggle.get_active()
            },
            "ui": {
                # "spellcheck": self.enable_spell_checker_toggle.get_active()
            }
        }


class LoggingPage(ttk.TTkFrame):

    def __init__(self, application):
        super().__init__(border=False, layout=ttk.TTkHBoxLayout())  # , name="logging")

        self.application = application

        self.scroll_area = ttk.TTkScrollArea(parent=self)  # , horizontalScrollBarPolicy=ttk.TTkK.ScrollBarAlwaysOff)
        self.content_box = ttk.TTkContainer(parent=self.scroll_area.viewport(), layout=ttk.TTkVBoxLayout())

        self.create_page(self.content_box)

        self.options = {
            "logging": {
                "privatechat": self.log_private_chat_toggle,
                # "privatelogsdir": self.private_chat_log_folder_button,
                "chatrooms": self.log_chatroom_toggle,
                # "roomlogsdir": self.chatroom_log_folder_button,
                "transfers": self.log_transfer_toggle,
                # "transferslogsdir": self.transfer_log_folder_button,
                "debug_file_output": self.log_debug_toggle,
                # "debuglogsdir": self.debug_log_folder_button,
                "log_timestamp": self.log_timestamp_format_entry
            }
        }

    def create_page(self, frame):

        group_containers = {}
        for group in [_("Logging"), _("Timestamps"), _("Folder Locations")]:
            group_container = group_containers[group] = ttk.TTkFrame(
                parent=frame, layout=ttk.TTkVBoxLayout(), title=group, titleAlign=ttk.TTkK.LEFT_ALIGN
            )
            group_container.layout().addWidget(ttk.TTkSpacer(minHeight=1))
            frame.layout().addWidget(ttk.TTkSpacer(minHeight=1))

        group_container = group_containers[_("Logging")]
        self.log_chatroom_toggle = CheckBox(parent=group_container, text=_("Log chatrooms by default"))
        self.log_private_chat_toggle = CheckBox(parent=group_container, text=_("Log private chat by default"))
        self.log_transfer_toggle = CheckBox(parent=group_container, text=_("Log transfers to file"))
        self.log_debug_toggle = CheckBox(parent=group_container, text=_("Log debug messages to file"))

        group_container = group_containers[_("Timestamps")]
        self.log_timestamp_format_entry = EntryBox(parent=group_container, label_text=_("Log timestamp format:"))
        format_codes_box = ttk.TTkContainer(parent=group_container, layout=ttk.TTkHBoxLayout(), padding=(0, 0, 0, 1))
        self.format_codes_label = ttk.TTkLabel(
            parent=format_codes_box,
            alignment=ttk.TTkK.RIGHT_ALIGN,
            text=ttk.TTkString(
                ("Format codes"),
                ttk.TTkColor.fg(URL_COLOR_HEX, link="https://docs.python.org/3/library/datetime.html#format-codes")
            )
        )

        # group_container = group_containers[_("Folder Locations")]

    def destroy(self):
        self.__dict__.clear()

    def resizeEvent(self, w: int, h: int):
        self.content_box.setGeometry(
            0, 0,
            max(w - 1, self.content_box.minimumWidth()), self.content_box.minimumHeight() - 1
        )

    def set_settings(self):
        self.application.preferences.set_widgets_data(self.options)

    def get_settings(self):
        return {
            "logging": {
                "privatechat": self.log_private_chat_toggle.get_active(),
                # "privatelogsdir": self.private_chat_log_folder_button.get_path(),
                "chatrooms": self.log_chatroom_toggle.get_active(),
                # "roomlogsdir": self.chatroom_log_folder_button.get_path(),
                "transfers": self.log_transfer_toggle.get_active(),
                # "transferslogsdir": self.transfer_log_folder_button.get_path(),
                "debug_file_output": self.log_debug_toggle.get_active(),
                # "debuglogsdir": self.debug_log_folder_button.get_path(),
                "log_timestamp": self.log_timestamp_format_entry.get_text()
            }
        }


class PluginsPage(ttk.TTkFrame):

    class PluginItem(ttk.TTkTreeWidgetItem):

        def __init__(self, data, **kwargs):

            self.plugin_name = data[0]  # .name()  # data[2]

            super().__init__(data, **kwargs)

            self.update_plugin_item()

        def is_enabled(self):
            return (self.plugin_name in config.sections["plugins"]["enabled"])

        def is_loaded(self):
            return (self.plugin_name in core.pluginhandler.enabled_plugins)

        def update_plugin_item(self):

            if not self.is_enabled():
                self.setIcon(0, ttk.TTkString("☖", ttk.TTkColor.RST))  # ▢
                text, color = "OFF", ttk.TTkColor.MAGENTA

            elif self.is_loaded():
                self.setIcon(0, ttk.TTkString("☗", ttk.TTkColor.GREEN + ttk.TTkColor.BOLD))  # ▣
                text, color = "ON", ttk.TTkColor.GREEN + ttk.TTkColor.BOLD

            else:
                self.setIcon(0, ttk.TTkString("⍉", ttk.TTkColor.YELLOW + ttk.TTkColor.BLINKING))  # ♺ ⚉ ◈ ⍉ ⍁ ⍠ ⍨
                text, color = "FAIL", ttk.TTkColor.YELLOW

            self.data(0)._text, self.data(0)._colors = ttk.TTkString._parseAnsi(text, color=color)
            self.emitDataChanged()

    def __init__(self, application):
        super().__init__(layout=ttk.TTkLayout(), paddingRight=1, border=False)  # name="plugins")

        self.application = application
        self.selected_plugin = None

        self.group_containers = []
        self._orientation = None

        self.create_page(self)

        self.options = {
            "plugins": {
                "enable": self.enable_plugins_toggle
            }
        }

    def create_page(self, frame):

        self.plugin_list_container = ttk.TTkFrame(layout=ttk.TTkVBoxLayout(), title=_("Plugins"))

        self.enable_plugins_toggle = CheckBox(parent=self.plugin_list_container, text=_("Enable plugins"))
        self.enable_plugins_toggle.toggled.connect(self.on_enable_plugins_toggled)

        self.plugin_list_view = ttk.TTkTree(
            parent=self.plugin_list_container,
            header=[_("Enabled"), _("Plugin")],
            minHeight=3
        )
        self.plugin_list_view.setColumnWidth(0, 7)
        self.plugin_list_view.setColumnWidth(1, 25)
        self.plugin_list_view.itemClicked.connect(self.on_select_plugin)
        self.plugin_list_view.itemActivated.connect(self.on_row_activated)

        buttons_box = ttk.TTkContainer(
            parent=self.plugin_list_container, layout=ttk.TTkHBoxLayout(), maxHeight=1, paddingLeft=1, paddingRight=1
        )
        self.install_plugin_button = ttk.TTkButton(parent=buttons_box, text=_("_Install…"))
        _button_spacer = ttk.TTkSpacer(parent=buttons_box)
        self.plugin_settings_button = ttk.TTkButton(parent=buttons_box, text=_("Settings"), enabled=False)
        self.plugin_settings_button.clicked.connect(self.on_plugin_settings)

        # View
        self.plugin_view_container = ttk.TTkFrame(layout=ttk.TTkVBoxLayout(), title=_("No Plugin Selected"))
        self.plugin_version_label = ttk.TTkLabel(parent=self.plugin_view_container, text=_("Version:"), maxHeight=1)
        self.plugin_authors_label = ttk.TTkLabel(parent=self.plugin_view_container, text=_("Created by:"), maxHeight=2)

        self.plugin_info_bar = ttk.TTkTextEdit(parent=self.plugin_view_container, readOnly=True, maxHeight=3)
        self.plugin_info_bar.setLineWrapMode(ttk.TTkK.WidgetWidth)
        self.plugin_info_bar.setWordWrapMode(ttk.TTkK.WordWrap)

        self.plugin_description_view = ttk.TTkTextEdit(parent=self.plugin_view_container, readOnly=True)
        self.plugin_description_view.setLineWrapMode(ttk.TTkK.WidgetWidth)
        self.plugin_description_view.setWordWrapMode(ttk.TTkK.WordWrap)

        # frame.layout().addWidget(self.plugin_list_container)
        # frame.layout().addWidget(self.plugin_view_container)
        self.group_containers = [self.plugin_list_container, self.plugin_view_container]
        self.resizeEvent(*self.size())

    def resizeEvent(self, w: int, h: int):

        if (w < self.plugin_list_container.minimumWidth() + self.plugin_view_container.minimumWidth()) or w < (h * 2):
            self.setOrientation(ttk.TTkK.Direction.VERTICAL)
        else:
            self.setOrientation(ttk.TTkK.Direction.HORIZONTAL)

    def setOrientation(self, orientation: ttk.TTkK.Direction):

        if orientation == self._orientation:
            return

        self.layout().clear()

        if orientation == ttk.TTkK.Direction.HORIZONTAL:
            self.setLayout(layout=ttk.TTkHBoxLayout())
            self._orientation = ttk.TTkK.Direction.HORIZONTAL

        elif orientation == ttk.TTkK.Direction.VERTICAL:
            self.setLayout(layout=ttk.TTkVBoxLayout())
            self._orientation = ttk.TTkK.Direction.VERTICAL

        self.layout().addWidgets(self.group_containers)

    def destroy(self):

        # self.plugin_popup_menu.destroy()
        self.plugin_info_bar.close()
        self.plugin_description_view.close()
        self.plugin_list_view.close()

        self.__dict__.clear()

    def set_settings(self):

        self.plugin_list_view.clear()
        self.plugin_list_view._treeView.setSortingEnabled(False)

        self.application.preferences.set_widgets_data(self.options)

        is_system_enabled = self.plugin_list_view.isEnabled()

        for plugin_name in core.pluginhandler.list_installed_plugins():
            try:
                plugin_info = core.pluginhandler.get_plugin_info(plugin_name)
            except OSError:
                continue

            plugin_human_name = plugin_info.get("Name", plugin_name)
            plugin_item = self.PluginItem([plugin_name, plugin_human_name], hidden=(not is_system_enabled))
            self.plugin_list_view.addTopLevelItem(plugin_item)

        self.plugin_list_view._treeView.setSortingEnabled(True)
        self.plugin_list_view.sortItems(1, ttk.TTkK.AscendingOrder)  # Plugin Name

    def get_settings(self):

        return {
            "plugins": {
                "enable": self.enable_plugins_toggle.get_active()
            }
        }

    def check_plugin_settings_button(self, plugin_name):
        self.plugin_settings_button.setEnabled(bool(core.pluginhandler.get_plugin_metasettings(plugin_name)))

    @ttk.pyTTkSlot(bool)
    def on_enable_plugins_toggled(self, is_system_enabled):

        self.selected_plugin = None
        self.plugin_list_view.clearSelection()
        self.plugin_list_view.setEnabled(is_system_enabled)
        self.install_plugin_button.setEnabled(is_system_enabled)
        self.on_select_plugin(None, -1)

        plugins_enabled = config.sections["plugins"]["enabled"].copy()
        plugins_loaded = core.pluginhandler.enabled_plugins.copy()

        if is_system_enabled:
            # Enable all selected plugins
            for plugin_name in plugins_enabled:
                core.pluginhandler.enable_plugin(plugin_name)
        else:
            # Disable all plugins
            for plugin_name in plugins_loaded:
                core.pluginhandler.disable_plugin(plugin_name, is_permanent=False)

        # config.sections["plugins"]["enabled"] = plugins_enabled

        for plugin_item in self.plugin_list_view.invisibleRootItem().children():
            plugin_item.setHidden(not is_system_enabled)
            plugin_item.update_plugin_item()

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_select_plugin(self, plugin_item, col):

        if col == 0:
            core.pluginhandler.toggle_plugin(plugin_item.plugin_name)
            plugin_item.update_plugin_item()

        if plugin_item is None:
            self.selected_plugin = _("No Plugin Selected")
            info = {}
        else:
            self.selected_plugin = plugin_item.plugin_name
            info = core.pluginhandler.get_plugin_info(self.selected_plugin)

        plugin_human_name = info.get("Name", self.selected_plugin)
        plugin_version = info.get("Version", "-")
        plugin_authors = ", ".join(info.get("Authors", "-"))
        plugin_description = info.get("Description", "").replace(r"\n", "\n")

        self.plugin_view_container.setTitle(plugin_human_name)
        self.plugin_version_label.setText(_("Version:") + " " + plugin_version)
        self.plugin_authors_label.setText(_("Created by:") + " " + plugin_authors)

        self.plugin_description_view.clear()
        self.plugin_description_view.setText(plugin_description)

        if plugin_item is not None and not core.pluginhandler.is_internal_plugin(self.selected_plugin):
            if plugin_item.is_enabled() and not plugin_item.is_loaded():
                info_text = "Unable to load third-party plugin. View the log for details."
            else:
                info_text = _("This is a third-party plugin. Safety is not guaranteed. Use at your own risk.")

            self.plugin_info_bar.setText(ttk.TTkString(info_text, ttk.TTkColor.ITALIC + ttk.TTkColor.YELLOW))
            self.plugin_info_bar.show()
        else:
            self.plugin_info_bar.hide()
            self.plugin_info_bar.setText("")

        self.check_plugin_settings_button(self.selected_plugin)

    @ttk.pyTTkSlot()
    def on_plugin_settings(self):
        self.application.on_plugin_settings(plugin_name=self.selected_plugin)

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_row_activated(self, list_item, col):
        if col == 1:
            self.on_plugin_settings()


class Preferences(Dialog):

    def __init__(self, application):

        self.application = application

        buttons_box = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), paddingLeft=1, paddingRight=1, maxHeight=3)
        self.export_button = ttk.TTkButton(parent=buttons_box, text=_("E_xport…"), border=True)
        self.export_button.clicked.connect(self.on_back_up_config)
        self.nav_spacer = ttk.TTkSpacer(parent=buttons_box)
        self.cancel_button = ttk.TTkButton(parent=buttons_box, text=_("_Cancel"), border=True)
        self.cancel_button.clicked.connect(self.on_cancel)
        self.apply_button = ttk.TTkButton(parent=buttons_box, text=_("A_pply"), border=True)
        self.apply_button.clicked.connect(self.on_apply)
        self.ok_button = ttk.TTkButton(parent=buttons_box, text=_("_OK"), border=True)
        self.ok_button.clicked.connect(self.on_ok)

        content_box = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), paddingLeft=1)  # , paddingRight=1)
        self.splitter = ttk.TTkSplitter(parent=content_box)  # orientation=ttk.TTkK.VERTICAL)
        self.splitter.addWidget(ttk.TTkSpacer())
        self.splitter.addWidget(ttk.TTkSpacer())

        self.preferences_list = ListBox(parent=None)  # , title="Section")
        self.preferences_list.itemClicked.connect(self.on_switch_page)

        self.preferences_drop = DropDownListBox(parent=None)  # , label_text="Section")
        self.preferences_drop.currentIndexChanged.connect(self.set_active_page_id)

        super().__init__(
            parent=application._instance,  # screen,
            content_box=content_box,
            buttons_box=buttons_box,
            default_widget=self.preferences_list,
            show_callback=self.on_show,
            close_callback=self.on_close,
            title=_("Preferences"),
            width=100,
            height=36,
            modal=True
            # show_title=False
        )

        self.pages = {}
        self.page_frames = [
            # ("network", NetworkPage, _("Network"), "network-wireless-symbolic"),
            # ("user-interface", UserInterfacePage, _("User Interface"), "view-grid-symbolic"),
            ("shares", SharesPage, _("Shares"), "folder-symbolic"),
            ("downloads", DownloadsPage, _("Downloads"), "folder-download-symbolic"),
            ("uploads", UploadsPage, _("Uploads"), "emblem-shared-symbolic"),
            # ("searches", SearchesPage, _("Searches"), "system-search-symbolic"),
            # ("user-profile", UserProfilePage, _("User Profile"), "avatar-default-symbolic"),
            ("chats", ChatsPage, _("Chats"), "insert-text-symbolic"),
            # ("now-playing", NowPlayingPage, _("Now Playing"), "folder-music-symbolic"),
            ("logging", LoggingPage, _("Logging"), "folder-documents-symbolic"),
            # ("banned-users", BannedUsersPage, _("Banned Users"), "action-unavailable-symbolic"),
            # ("ignored-users", IgnoredUsersPage, _("Ignored Users"), "microphone-sensitivity-muted-symbolic"),
            # ("url-handlers", UrlHandlersPage, _("URL Handlers"), "insert-link-symbolic"),
            ("plugins", PluginsPage, _("Plugins"), "application-x-addon-symbolic")
        ]

        for page_data in self.page_frames:  # [:]
            page_name, page_class, page_label, page_icon = page_data
            self.preferences_list.addItem(f" {page_label}", page_data)  # list[TTkListItem]
            self.preferences_drop.addItem(page_label)                   # list[str]

        self.preferences_list.setMinimumWidth(max(len(list_item.text()) for list_item in self.preferences_list.items()))

    def destroy(self):

        self.export_button.clicked.disconnect(self.on_back_up_config)
        self.cancel_button.clicked.disconnect(self.on_cancel)
        self.apply_button.clicked.disconnect(self.on_apply)
        self.ok_button.clicked.disconnect(self.on_ok)
        self.preferences_list.itemClicked.disconnect(self.on_switch_page)

        for page in self.pages.values():
            page.destroy()

        self.splitter.clean()
        super().destroy()

    def on_show(self, window):

        window.setWindowFlag(ttk.TTkK.WindowFlag.WindowMaximizeButtonHint | ttk.TTkK.WindowFlag.WindowCloseButtonHint)
        window.sizeChanged.connect(self.on_resize)
        self.on_resize(*window.size())

        self.set_active_page(self.get_active_page())  # reload settings

    @ttk.pyTTkSlot(int, int)
    def on_resize(self, w: int, h: int):

        if w <= 60:  # or (self.content_box.width() <= self.content_box.minimumWidth()):  # w < (h * 1.5)
            self.splitter.setOrientation(ttk.TTkK.VERTICAL)
            self.splitter.replaceWidget(0, self.preferences_drop.parentWidget())  # Box
            self.splitter.setSizes([2, None])  # 77
        else:
            self.splitter.setOrientation(ttk.TTkK.HORIZONTAL)
            self.splitter.replaceWidget(0, self.preferences_list.parentWidget())  # Frame
            self.splitter.setSizes([self.preferences_list.minimumWidth() + 4, None])  # 77

    def get_active_page(self):
        page_name = ""
        for page_item in self.preferences_list.selectedItems():
            page_name, page_class, page_label, page_icon = page_item.data()
            break
        return page_name

    @ttk.pyTTkSlot(int)
    def set_active_page_id(self, page_id):
        page_item = self.preferences_list.itemAt(page_id)
        self.preferences_list.setCurrentItem(page_item)

    @ttk.pyTTkSlot(ttk.TTkAbstractListItem)
    def on_switch_page(self, page_item):

        page_name, page_class, page_label, page_icon = page_item.data()

        if page_name not in self.pages:
            self.pages[page_name] = page = page_class(self.application)
            page.set_settings()

        self.splitter.replaceWidget(1, self.pages[page_name])

    def set_active_page(self, page_name):

        for page_item in self.preferences_list.items():
            n_page_name, page_class, page_label, page_icon = page_item.data()

            if n_page_name != page_name:
                continue

            self.preferences_list.setCurrentItem(page_item)
            break

    def set_widgets_data(self, options):

        for section, keys in options.items():
            if section not in config.sections:
                continue

            for key in keys:
                widget = options[section][key]

                if widget is None:
                    continue

                self.set_widget(widget, config.sections[section][key])

    @staticmethod
    def set_widget(widget, value):

        if isinstance(widget, CheckBox):
            widget.set_active(value)

        if isinstance(widget, ttk.TTkCheckbox):
            widget.setChecked(value)
            widget.toggled.emit(value)

        elif isinstance(widget, DropDownListBox):
            if isinstance(value, int):
                widget.set_selected_id(value)
            elif isinstance(value, str):
                widget.set_text(value)

        elif isinstance(widget, ttk.TTkComboBox):
            if isinstance(value, int):
                widget.setCurrentIndex(value)
            # elif isinstance(value, str):
            #     widget.setCurrentText(value)

        elif isinstance(widget, EntryBox):
            if isinstance(value, (str, int)) and widget.get_text() != value:
                widget.set_text(str(value))

        # elif isinstance(widget, ttk.TTkLineEdit):
        #     if isinstance(value, (str, int)) and str(widget.text()) != value:
        #         widget.setText(str(value))

        elif isinstance(widget, SpinBox):
            # if isinstance(value, int):
            widget.set_value(value)

        # elif isinstance(widget, ttk.TTkSpinBox):
        #     try:
        #         widget.setValue(value)
        #     except TypeError:
        #         pass  # Not a numerical value

        # elif isinstance(widget, ttk.TTkFileButtonPicker):
        elif isinstance(widget, FileChooserButton):
            # widget.setPath(value)
            widget.set_path(value)

    def set_settings(self):

        for page in self.pages.values():
            page.set_settings()

    def get_settings(self):

        options = {
            "server": {},
            "transfers": {},
            # "userinfo": {},
            "logging": {},
            # "searches": {},
            "privatechat": {},
            "ui": {},
            # "urls": {},
            # "players": {},
            "words": {},
            # "notifications": {},
            "plugins": {}
        }

        for page in self.pages.values():
            for key, data in page.get_settings().items():
                options[key].update(data)

        return options

    @staticmethod
    def has_modified_options(options, section, keys):
        return any((key in options[section] and options[section][key] != config.sections[section][key]) for key in keys)

    def update_settings(self, settings_closed=False):

        options = self.get_settings()

        # reconnect_required,
        # portmap_required,
        rescan_required = self.has_modified_options(
            options, "transfers", ["shared", "buddyshared", "trustedshared", "share_filters"])

        rescan_daily_required = self.has_modified_options(
            options, "transfers", ["rescan_shares_daily", "rescan_shares_hour"])

        recompress_shares_required = self.has_modified_options(
            options, "transfers", ["reveal_buddy_shares", "reveal_trusted_shares"])

        # user_profile_required,
        # private_room_required,
        # completion_required,
        # search_history_required,

        for key, data in options.items():
            config.sections[key].update(data)

        if not rescan_required:
            if rescan_daily_required:
                core.shares.start_rescan_daily_timer()

            if recompress_shares_required:
                core.shares.rescan_shares(init=True, rescan=False)

        # Update configuration
        config.write_configuration()

        if not settings_closed:
            return

        self.close()

        if rescan_required:
            core.shares.rescan_shares()

        if config.need_config():
            core.setup()

    @ttk.pyTTkSlot()
    def on_back_up_config(self, *_args):
        pass  # #

    @ttk.pyTTkSlot()
    def on_cancel(self):
        self.close()

    @ttk.pyTTkSlot()
    def on_apply(self, *_args):
        self.update_settings()

    @ttk.pyTTkSlot()
    def on_ok(self):
        self.update_settings(settings_closed=True)

    def on_close(self, window):
        # self.content.get_vadjustment().set_value(0)
        window.sizeChanged.disconnect(self.on_resize)
        self.application.screen.focus_default_widget()
