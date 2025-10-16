# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2009-2011 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
#from pynicotine.gtkgui.application import GTK_API_VERSION
#from pynicotine.gtkgui.widgets import ui
#from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
#from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.ttktui.widgets.dialogs import Dialog
#from pynicotine.gtkgui.widgets.dialogs import EntryDialog
#from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
#from pynicotine.gtkgui.widgets.treeview import TreeView
#from pynicotine.slskmessages import UserStatus


class FastConfigure(Dialog):

    def __init__(self, application):

        self.invalid_password = False
        self.rescan_required = False
        self.finished = False

        #self.pages = [self.welcome_page, self.account_page, self.port_page, self.share_page, self.summary_page]

        super().__init__(
            parent=application.screen,
            #content_box=self.stack,
            #buttons_start=(self.previous_button,),
            #buttons_end=(self.next_button,),
            #default_button=self.next_button,
            show_callback=self.on_show,
            close_callback=self.on_close,
            title=_("Setup Assistant"),
            width=72,
            height=25,
            modal=True
            #show_title=False
        )

    def on_close(self, *_args):
        self.invalid_password = False
        self.rescan_required = False

    def on_show(self, *_args):

        self.window.setWindowFlag(ttk.TTkK.WindowFlag.WindowCloseButtonHint |
                                  ttk.TTkK.WindowFlag.WindowMaximizeButtonHint)

        pass
