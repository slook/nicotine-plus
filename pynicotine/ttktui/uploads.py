# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2009-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2009 hedonist <ak@sensi.org>
# SPDX-FileCopyrightText: 2006-2008 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

#from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.transfers import Transfers
from pynicotine.ttktui.transfers import TransfersTree


class UploadsTree(TransfersTree):

    class UploadItem(TransfersTree.TransferItem):
        pass

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)


class Uploads(Transfers):

    def __init__(self, screen, name="upload"):
        super().__init__(screen, name=name)

        self.placeholder.setText(
            _("Users' attempts to download your shared files are queued and managed here") + "\n\nNOT IMPLEMENTED"
        )

        for widget in [self.users_button, self.files_button]:
            widget.setToolTip(self.placeholder.text())

        self.tree = UploadsTree(parent=self.tree_container, name=name, visible=True)

        self._abort_button = ttk.TTkButton(parent=self.buttons_left, text=_("Abor_t"))
        self._abort_users_button = ttk.TTkButton(parent=self.buttons_left, text=_("Abort _Users"))
        self._message_all_button = ttk.TTkButton(parent=self.buttons_right, text=_("Message All"))
        self._clear_finished_button = ttk.TTkButton(parent=self.buttons_right, text=_("Clear Finished"))
        self.clear_all_button = ttk.TTkButton(parent=self.buttons_right, text=_("Clear _All…"))

        # Events
        for event_name, callback in (
            #("abort-upload", self.abort_transfer),
            #("abort-uploads", self.abort_transfers),
            #("add-buddy", self.update_buddy),
            #("clear-upload", self.clear_transfer),
            #("clear-uploads", self.clear_transfers),
            #("remove-buddy", self.update_buddy),
            #("set-connection-stats", self.set_connection_stats),
            ("start", self.start),
            #("update-upload", self.update_model),
            #("update-upload-limits", self.update_limits),
            #("uploads-shutdown-request", self.shutdown_request),
            #("uploads-shutdown-cancel", self.shutdown_cancel)
        ):
            events.connect(event_name, callback)

    def start(self):
        events.schedule(delay=1, callback=self.init_uploads)

    def init_uploads(self):
        self.init_transfers(core.uploads.transfers.values())
