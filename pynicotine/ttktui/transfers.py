# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
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
from pynicotine.utils import human_length
from pynicotine.utils import human_size
from pynicotine.utils import human_speed


_KEY_COLUMN = 0  # ("User")


class _TransferItem(Tree.Item):

    def setData(self, column, value, color=None, emit=True):

        # Hack the new value into the existing string object of the model
        self.data(column)._text, self.data(column)._colors = ttk.TTkString._parseAnsi(str(value), color=color)

        if emit:
            self.emitDataChanged()


class FileItem(_TransferItem):

    def __init__(self, basename, transfer, **kwargs):

        self.transfer = transfer

        super().__init__([
            basename,
            f"{self.get_hsize():>20}",
            f"{self.get_percent():3d}%",
            transfer.status,
            self.get_hqueue_position(),
            self.get_hspeed(),
            self.get_helapsed(),
            self.get_hleft()
        ], **kwargs)

    def update_row(self, transfer):

        self.transfer = transfer

        for column, value in enumerate([
            str(self.data(0)),
            f"{self.get_hsize():>20}",
            f"{self.get_percent():3d}%",
            self.transfer.status,
            self.get_hqueue_position(),
            self.get_hspeed(),
            self.get_helapsed(),
            self.get_hleft()
        ]):
            if str(self.data(column)) != value:
                self.setData(column, value, emit=(column == 7))

    def sortData(self, column):

        if column == 1:
            return self.transfer.size or 0

        if column == 2:
            return self.get_percent()

        return str(self.data(column)).lower()

    def get_hqueue_position(self):
        return str(self.transfer.queue_position) if self.transfer.queue_position > 0 else ""

    def get_hsize(self):

        if not self.transfer.current_byte_offset or self.transfer.current_byte_offset >= self.transfer.size:
            return human_size(self.transfer.size)

        return f"{human_size(self.transfer.current_byte_offset)} / {human_size(self.transfer.size)}"

    def get_hspeed(self):
        return human_speed(self.transfer.speed) if self.transfer.speed > 0 else ""

    def get_helapsed(self):
        return human_length(self.transfer.time_elapsed) if self.transfer.time_elapsed > 0 else ""

    def get_hleft(self):
        return human_length(self.transfer.time_left) if self.transfer.time_left >= 1 else ""

    def get_percent(self):

        if not self.transfer.current_byte_offset:
            return 0

        if self.transfer.current_byte_offset > self.transfer.size or self.transfer.size <= 0:
            return 100

        # Multiply first to avoid decimals
        return (100 * self.transfer.current_byte_offset) // self.transfer.size


class FolderItem(_TransferItem):

    def __init__(self, folder_path, **kwargs):

        #self._folder_path = data[0]
        #_parent_path, _separator, folder_name = self._folder_path.rpartition("\\")
        #data[0] = folder_name

        super().__init__([folder_path, "", "", "", "", "", "", ""], expanded=True, **kwargs)

        self.file_items = {}

    def add_file_row(self, basename, transfer):
        """Creates a FileItem() from a list of values and adds an iterator"""

        self.file_items[basename] = file_item = FileItem(basename, transfer, parent=self)  # , **kwargs)

        self.setData(1, len(self.file_items), emit=False)

        return file_item

    def setData(self, column, value, color=None, emit=True):

        if column == 1:
            value = f"{value} Files" if value > 0 else ""
            color = ttk.TTkColor.fg("#888888") + ttk.TTkColor.ITALIC

        super().setData(column, value, color=color, emit=emit)

    def sortData(self, column):

        if column == 1:
            return len(self.file_items)

        return str(self.data(column)).lower()


class UserItem(_TransferItem):

    def __init__(self, username, **kwargs):
        super().__init__([username, "", "", "", "", "", "", ""], expanded=True, **kwargs)

        self.total_file_size = 0
        self.folder_items = {}

    def add_folder_row(self, folder_path):
        """Creates a FolderItem() from a list of values and adds an iterator"""

        self.folder_items[folder_path] = folder_item = FolderItem(folder_path, parent=self)  # , **kwargs)

        #self.addChild(folder_item)

        return folder_item


class TransfersTree(Tree):

    class TransferItem(_TransferItem):
        pass

    def __init__(self, parent=None, **kwargs):
        super().__init__(
            parent=parent,
            header=[
                #_("User"),      # 0
                #_("Folder"),    # 1
                #" ",            # 2 file type icon
                #_("Filename"),  # 3
                f'{(_("User"))} / {(_("Folder"))} / {(_("Filename"))}',  # 3
                _("Size"),      # 4
                _("Percent"),   # 5
                _("Status"),    # 6
                _("Queue"),     # 7
                _("Speed"),     # 8
                _("Time Elapsed"),
                _("Time Left")
            ],
            **kwargs
        )

        # Columns                    0  *1   2   3   4   5   6  7   8   9  10
        for col, width in enumerate([50, 20, 10, 18, 8, 12, 12, 12]):
            self.setColumnWidth(col, width)

        self.user_items = {}

    def readd_user_items(self):
        """This method avoids individually painting each row."""

        self.clear()
        self.addTopLevelItems(list(self.user_items.values()))

    def add_user_row(self, username):
        """Creates a UserItem() from a list of values and adds an iterator"""

        self.user_items[username] = user_item = UserItem(username)  # , **kwargs)

        self.addTopLevelItem(user_item)

        return user_item


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

        self.header_bar.layout().addWidget(ttk.TTkSpacer(maxWidth=5))

        self.files_button = ttk.TTkButton(
            parent=self.header_bar,
            text=ttk.TTkString(_("Files"), ttk.TTkColor.BOLD),
            minWidth=10, maxWidth=10
        )

        self.header_bar.layout().addWidget(ttk.TTkSpacer())

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout(), visible=True)
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=self.screen.TAB_LABELS[f"{name}s"]
        )
        self.placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        self.content = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout(), visible=False)

        self.tree_container = ttk.TTkContainer(parent=self.content, layout=ttk.TTkVBoxLayout())

        self.buttons_bar = ttk.TTkContainer(parent=self.content, layout=ttk.TTkHBoxLayout(), maxHeight=1)
        self.buttons_left = ttk.TTkContainer(parent=self.buttons_bar, layout=ttk.TTkHBoxLayout())
        self.buttons_mid = ttk.TTkContainer(parent=self.buttons_bar, layout=ttk.TTkHBoxLayout())
        self.buttons_right = ttk.TTkContainer(parent=self.buttons_bar, layout=ttk.TTkHBoxLayout())

        #self.transfer_list = {}
        #self.initialized = False

    def connect_signals(self):
        self.screen.tab_bar.currentChanged.connect(self.on_focus_tab)

    def focus_default_widget(self):

        if self.content.isVisible():
            self.tree.setFocus()
        else:
            self.users_button.setFocus()

    @ttk.pyTTkSlot(int)
    def on_focus_tab(self, _tab_number):
        if self.screen.tab_bar.currentWidget() == self:
            self.screen.setWidget(widget=self.header_bar, position=self.screen.HEADER)

            #self.update_model()
            self.focus_default_widget()

    def init_transfers(self, transfer_list):

        #self.transfer_list = transfer_list

        for transfer in transfer_list:
            user_item = self.tree.user_items.get(transfer.username, None)

            if user_item is None:
                user_item = self.tree.add_user_row(transfer.username)

            folder_path, separator, basename = transfer.virtual_path.rpartition("\\")
            folder_item = user_item.folder_items.get(folder_path, None)

            if folder_item is None:
                folder_item = user_item.add_folder_row(folder_path)

            file_item = folder_item.file_items.get(basename, None)

            if file_item is None:
                file_item = folder_item.add_file_row(basename, transfer)

            transfer.iterator = file_item

            #folder_item.setExpanded(True)
            #user_item.setExpanded(True)

        #self.tree.readd_user_items()
        #self.tree.expandAll()

        self.content.setVisible(bool(transfer_list))
        self._spacer.setVisible(not self.content.isVisible())
        #self.initialized = True

    def update_model(self, transfer=None, update_parent=True):
        pass
