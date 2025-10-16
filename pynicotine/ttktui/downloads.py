# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2016-2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2013 eLvErDe <gandalf@le-vert.net>
# SPDX-FileCopyrightText: 2008-2012 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2009 hedonist <ak@sensi.org>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-FileCopyrightText: 2003-2004 Nicotine Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

# from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
# from pynicotine.slskmessages import UserStatus
from pynicotine.transfers import TransferStatus
from pynicotine.ttktui.transfers import Transfers
from pynicotine.ttktui.transfers import TransfersTree
from pynicotine.utils import open_file_path
from pynicotine.utils import open_folder_path


class DownloadsTree(TransfersTree):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)


class Downloads(Transfers):

    def __init__(self, screen, name="downloads"):
        super().__init__(screen, name=name)

        self.placeholder.setText(
            _("Files you download from other users are queued here, "
              "and can be paused and resumed on demand").replace(", and", ",\nand")
        )

        self.tree = DownloadsTree(
            parent=self.tree_container, name=name, selectionMode=ttk.TTkK.SelectionMode.MultiSelection, visible=True
        )

        self._resume_button = ttk.TTkButton(parent=self.buttons_left, text=f'↪ {_("Re_sume")}')
        self._resume_button.clicked.connect(self.on_retry_transfer)

        self._pause_button = ttk.TTkButton(parent=self.buttons_left, text=f'▮▮ {_("_Pause")}')
        self._pause_button.clicked.connect(self.on_abort_transfer)

        self._remove_button = ttk.TTkButton(parent=self.buttons_left, text=f'━ {_("Remove")}')  # ━ ▬ ▰▰ ▰
        self._remove_button.clicked.connect(self.on_remove_transfer)

        self._clear_finished_button = ttk.TTkButton(parent=self.buttons_right, text=_("Clear Finished"))

        self.clear_all_button = ttk.TTkButton(parent=self.buttons_right, text=_("Clear _All…"))

        self.download_status_label = self.screen.status_bar.download_status_label

        # Events
        for event_name, callback in (
            ("abort-download", self.abort_transfer),
            # ("abort-downloads", self.abort_transfers),
            ("add-buddy", self.update_buddy),
            ("clear-download", self.clear_transfer),
            # ("clear-downloads", self.clear_transfers),
            # ("download-large-folder", self.download_large_folder),
            ("folder-download-finished", self.folder_download_finished),
            ("remove-buddy", self.update_buddy),
            ("set-connection-stats", self.set_connection_stats),
            ("start", self.start),
            ("update-download", self.update_model),
            # ("update-download-limits", self.update_limits),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def start(self):
        events.schedule(delay=2, callback=self.init_downloads)

    def init_downloads(self):
        self.init_transfers(core.downloads.transfers.values())

    def set_connection_stats(self, download_bandwidth=0, **_kwargs):

        # Sync parent row updates with connection stats
        # self._update_pending_parent_rows()

        download_speed = download_bandwidth // 1024  # Kb/s
        active_users = len(core.downloads.active_users)
        download_status_text = f"{download_speed:5d} KiB/s 🡳"

        if self.download_status_label.text() == download_status_text:
            return

        text_color = ttk.TTkColor.BOLD if download_bandwidth else ttk.TTkColor.RST
        icon_color = (ttk.TTkColor.BOLD + ttk.TTkColor.GREEN) if active_users else ttk.TTkColor.fg("#606060")

        self.download_status_label.setText(
            ttk.TTkString(download_status_text, text_color).setColorAt(len(download_status_text) - 1, icon_color)
        )
        self.download_status_label.setToolTip(
            _("Downloading: %(speed)s ( %(active_users)s )") % {
                "speed": f"{download_speed} KiB/s",
                "active_users": active_users
            }
        )

    def folder_download_finished(self, _folder_path):
        if self.screen.tab_bar.currentWidget() != self:
            self.screen.tab_bar.request_tab_changed(self, is_important=True)

    def open_file_manager(self, selected_transfers):

        from os.path import dirname  # #

        folder_path = None

        for download in selected_transfers:
            file_path = core.downloads.get_current_download_file_path(download)
            folder_path = dirname(file_path)

            if download.status == TransferStatus.FINISHED:
                # Prioritize finished downloads
                break

        open_folder_path(folder_path)

    def open_files(self, selected_transfers):

        for download in selected_transfers:
            file_path = core.downloads.get_current_download_file_path(download)
            open_file_path(file_path)

    def browse_folder(self, selected_transfer):

        # download = selected_transfer  # next(iter(self.selected_transfers), None)

        if not selected_transfer:
            return

        user = selected_transfer.username
        path = selected_transfer.virtual_path

        core.userbrowse.browse_user(user, path=path)

    def retry_selected_transfers(self, selected_transfers):
        core.downloads.retry_downloads(list(selected_transfers))

    def abort_selected_transfers(self, selected_transfers):
        core.downloads.abort_downloads(selected_transfers)

    def remove_selected_transfers(self, selected_transfers):
        core.downloads.clear_downloads(downloads=list(selected_transfers))
