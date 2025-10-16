# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2009 hedonist <ak@sensi.org>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

#from pynicotine.config import config
#from pynicotine.core import core
#from pynicotine.events import events
from pynicotine.ttktui.widgets.trees import Tree


class TransfersTree(Tree):

    class TransferItem(Tree.Item):
        pass

    def __init__(self, parent=None, **kwargs):
        super().__init__(
            parent=parent,
            header=[
                "0",         # 0
                "1",   # 1
                "2",  # 2
            ],
            **kwargs
        )

        # Columns                    0  *1  2  3   4  5  6  7   8   9  10
        for col, width in enumerate([3, 30, 8]):  # , 8, 12, 8, 8, 8, 12, 20, 40]):
            self.setColumnWidth(col, width)


class Transfers(ttk.TTkContainer):

    def __init__(self, screen, name=None):
        super().__init__(layout=ttk.TTkVBoxLayout(), name=name)

        self.screen = screen

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        self.header_bar.layout().addWidget(ttk.TTkSpacer())

        self.users_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(_("Users"), ttk.TTkColor.BOLD),
            minWidth=10, maxWidth=10
        )
        #self.users_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        #self.users_button.clicked.connect(self.on_entry_clicked)

        self.header_bar.layout().addWidget(ttk.TTkSpacer(maxWidth=5))

        self.files_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(_("Files"), ttk.TTkColor.BOLD),
            minWidth=10, maxWidth=10
        )
        #self.users_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        #self.users_button.clicked.connect(self.on_entry_clicked)

        self.header_bar.layout().addWidget(ttk.TTkSpacer())

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout())
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[name]
        )
        self.placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)
