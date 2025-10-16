# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2016-2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2013 eLvErDe <gandalf@le-vert.net>
# SPDX-FileCopyrightText: 2008-2012 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2009 hedonist <ak@sensi.org>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

#from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.transfers import Transfers
from pynicotine.ttktui.transfers import TransfersTree


class DownloadsTree(TransfersTree):

    class DownloadItem(TransfersTree.TransferItem):
        pass

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)


class Downloads(Transfers):

    def __init__(self, screen, name="download"):
        super().__init__(screen, name=name)

        self.placeholder.setText(
            _("Files you download from other users are queued here, "
              "and can be paused and resumed on demand").replace(", and", ",\nand") + "\n\nNOT IMPLEMENTED"
        )

        for widget in [self.users_button, self.files_button]:
            widget.setToolTip(self.placeholder.text())

        self.tree = DownloadsTree(parent=self.tree_container, name=name, visible=True)

        self._resume_button = ttk.TTkButton(parent=self.buttons_left, text=_("Re_sume"))
        self._pause_button = ttk.TTkButton(parent=self.buttons_left, text=_("_Pause"))
        self._remove_button = ttk.TTkButton(parent=self.buttons_left, text=_("Remove"))
        self._clear_finished_button = ttk.TTkButton(parent=self.buttons_right, text=_("Clear Finished"))
        self.clear_all_button = ttk.TTkButton(parent=self.buttons_right, text=_("Clear _All…"))

        # Events
        for event_name, callback in (
            #("abort-download", self.abort_transfer),
            #("abort-downloads", self.abort_transfers),
            #("add-buddy", self.update_buddy),
            #("clear-download", self.clear_transfer),
            #("clear-downloads", self.clear_transfers),
            #("download-large-folder", self.download_large_folder),
            #("folder-download-finished", self.folder_download_finished),
            #("remove-buddy", self.update_buddy),
            #("set-connection-stats", self.set_connection_stats),
            ("start", self.start),
            #("update-download", self.update_model),
            #("update-download-limits", self.update_limits)
        ):
            events.connect(event_name, callback)

    def start(self):
        events.schedule(delay=2, callback=self.init_downloads)

    def init_downloads(self):
        self.init_transfers(core.downloads.transfers.values())
