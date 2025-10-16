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
#from pynicotine.core import core
#from pynicotine.events import events
from pynicotine.ttktui.transfers import Transfers
from pynicotine.ttktui.transfers import TransfersTree


class DownloadsTree(TransfersTree):

    class DownloadItem(TransfersTree.TransferItem):
        pass

    def __init__(self, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs)


class Downloads(Transfers):

    def __init__(self, screen, name="downloads"):
        super().__init__(screen, name=name)

        self.placeholder.setText(
            _("Files you download from other users are queued here, "
              "and can be paused and resumed on demand").replace(", and", ",\nand") + "\n\nNOT IMPLEMENTED"
        )

        for widget in [self.users_button, self.files_button]:
            widget.setToolTip(self.placeholder.text())

        self.tree = DownloadsTree(parent=self, name=name, visible=False)

        # Events


    def connect_signals(self):
        self.screen.tab_bar.currentChanged.connect(self.on_focus_tab)

    def focus_default_widget(self):
        self.users_button.setFocus()

    @ttk.pyTTkSlot(int)
    def on_focus_tab(self, _tab_number):
        if self.screen.tab_bar.currentWidget() == self:
            self.screen.setWidget(widget=self.header_bar, position=self.screen.HEADER)
            self.focus_default_widget()
