# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2009-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2009 hedonist <ak@sensi.org>
# SPDX-FileCopyrightText: 2006-2008 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-FileCopyrightText: 2003-2004 Nicotine Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

# from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
# from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.transfers import Transfers
from pynicotine.ttktui.transfers import TransfersTree
from pynicotine.utils import open_file_path
from pynicotine.utils import open_folder_path


class UploadsTree(TransfersTree):

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)


class Uploads(Transfers):

    def __init__(self, screen, name="uploads"):
        super().__init__(screen, name=name)

        self.placeholder.setText(_("Users' attempts to download your shared files are queued and managed here"))

        self.tree = UploadsTree(
            parent=self.tree_container, name=name, selectionMode=ttk.TTkK.SelectionMode.MultiSelection, visible=True
        )

        self._abort_button = ttk.TTkButton(parent=self.buttons_left, text=f'■ {_("Abor_t")}')
        self._abort_button.clicked.connect(self.on_abort_transfer)

        self._abort_users_button = ttk.TTkButton(parent=self.buttons_left, text=f'⏏ {_("Abort _Users")}')
        self._abort_users_button.clicked.connect(self.on_abort_users)

        self._message_all_button = ttk.TTkButton(parent=self.buttons_right, text=_("Message All"))
        self._clear_finished_button = ttk.TTkButton(parent=self.buttons_right, text=_("Clear Finished"))
        self.clear_all_button = ttk.TTkButton(parent=self.buttons_right, text=_("Clear _All…"))

        self.upload_status_label = self.screen.status_bar.upload_status_label

        # Events
        for event_name, callback in (
            ("abort-upload", self.abort_transfer),
            # ("abort-uploads", self.abort_transfers),
            ("add-buddy", self.update_buddy),
            ("clear-upload", self.clear_transfer),
            # ("clear-uploads", self.clear_transfers),
            ("remove-buddy", self.update_buddy),
            ("set-connection-stats", self.set_connection_stats),
            ("start", self.start),
            ("update-upload", self.update_model),
            # ("update-upload-limits", self.update_limits),
            # ("uploads-shutdown-request", self.shutdown_request),
            # ("uploads-shutdown-cancel", self.shutdown_cancel),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def start(self):
        events.schedule(delay=1, callback=self.init_uploads)

    def init_uploads(self):
        self.init_transfers(core.uploads.transfers.values())

    def set_connection_stats(self, upload_bandwidth=0, **_kwargs):

        # Sync parent row updates with connection stats
        # self._update_pending_parent_rows()

        upload_speed = upload_bandwidth // 1024  # Kb/s
        active_users = len(core.uploads.active_users)
        upload_status_text = f"{upload_speed:5d} KiB/s 🡱"

        if self.upload_status_label.text() == upload_status_text:
            return

        text_color = ttk.TTkColor.BOLD if upload_bandwidth else ttk.TTkColor.RST
        icon_color = (ttk.TTkColor.BOLD + ttk.TTkColor.YELLOW) if active_users else ttk.TTkColor.fg("#606060")

        self.upload_status_label.setText(
            ttk.TTkString(upload_status_text, text_color).setColorAt(len(upload_status_text) - 1, icon_color)
        )
        self.upload_status_label.setToolTip(
            _("Uploading: %(speed)s ( %(active_users)s )") % {
                "speed": f"{upload_speed} KiB/s",
                "active_users": active_users
            }
        )

    def open_file_manager(self, selected_transfers):

        upload = next(iter(selected_transfers), None)

        if upload:
            open_folder_path(upload.folder_path)

    def open_files(self, selected_transfers):

        from os.path import join  # #

        for upload in selected_transfers:
            basename = upload.virtual_path.rpartition("\\")[-1]

            open_file_path(join(upload.folder_path, basename))

    def browse_folder(self, selected_transfer):

        # transfer = selected_transfer  # next(iter(self.selected_transfers), None)

        if not selected_transfer:
            return

        from pynicotine.config import config  # #
        user = config.sections["server"]["login"]
        path = selected_transfer.virtual_path

        core.userbrowse.browse_user(user, path=path)

    def retry_selected_transfers(self, selected_transfers):
        core.uploads.retry_uploads(list(selected_transfers))

    def abort_selected_transfers(self, selected_transfers):
        core.uploads.abort_uploads(selected_transfers, denied_message="Cancelled")

    def remove_selected_transfers(self, selected_transfers):
        core.uploads.clear_uploads(uploads=selected_transfers)

    def on_abort_users(self, *_args):
        self.abort_selected_transfers(self.tree.get_selected_file_transfers(select_users=True))
