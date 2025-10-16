# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2018 Mutnick <mutnick@techie.com>
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2009 hedonist <ak@sensi.org>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-FileCopyrightText: 2003-2004 Nicotine Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
# from pynicotine.events import events
from pynicotine.slskmessages import TransferRejectReason
# from pynicotine.slskmessages import UserStatus
from pynicotine.transfers import TransferStatus
from pynicotine.ttktui.widgets.menus import FilePopupMenu
from pynicotine.ttktui.widgets.theme import USER_STATUS_COLORS
from pynicotine.ttktui.widgets.theme import USERNAME_STYLE
from pynicotine.ttktui.widgets.trees import Tree
from pynicotine.utils import human_length
from pynicotine.utils import human_size
from pynicotine.utils import human_speed


# TODO: Move this duplicated from gtkgui into the core transfers module
STATUSES = {
    TransferStatus.QUEUED: _("Queued"),
    f"{TransferStatus.QUEUED} (prioritized)": _("Queued (prioritized)"),
    f"{TransferStatus.QUEUED} (privileged)": _("Queued (privileged)"),
    TransferStatus.GETTING_STATUS: _("Getting status"),
    TransferStatus.TRANSFERRING: _("Transferring"),
    TransferStatus.CONNECTION_CLOSED: _("Connection closed"),
    TransferStatus.CONNECTION_TIMEOUT: _("Connection timeout"),
    TransferStatus.USER_LOGGED_OFF: _("User logged off"),
    TransferStatus.PAUSED: _("Paused"),
    TransferStatus.CANCELLED: _("Cancelled"),
    TransferStatus.FINISHED: _("Finished"),
    TransferStatus.FILTERED: _("Filtered"),
    TransferStatus.DOWNLOAD_FOLDER_ERROR: _("Download folder error"),
    TransferStatus.LOCAL_FILE_ERROR: _("Local file error"),
    TransferRejectReason.BANNED: _("Banned"),
    TransferRejectReason.FILE_NOT_SHARED: _("File not shared"),
    TransferRejectReason.PENDING_SHUTDOWN: _("Pending shutdown"),
    TransferRejectReason.FILE_READ_ERROR: _("File read error")
}


class TransferColumn:
    NAME = 0
    SIZE = 1
    PERCENT = 2
    STATUS = 3
    QUEUE = 4
    SPEED = 5
    TIME_ELAPSED = 6
    TIME_LEFT = 7

    # Hidden Columns
    # _KEY = 8


class _TransferItem(Tree.Item):
    """Base class for a UserItem, FolderItem or FileItem row of TransferTree."""

    __slots__ = ("status",)

    def __init__(self, values, **kwargs):

        self.status = values[3]
        values[3] = self.get_translated_status(self.status)

        super().__init__(values, **kwargs)

    # def name(self):
    #     return str(self.data(TransferColumn.NAME))

    def parent(self):
        return self._parent

    def setData(self, column, value, color=None, emit=True):

        # if column == TransferColumn._KEY:
        #     raise KeyError(f'Cannot rename tree item key data "{str(self.data(TransferColumn._KEY))}" to "{value}"')

        if column == TransferColumn.STATUS:
            if self.status == value:
                return

            if value in {  # .endswith("error"):
                TransferStatus.DOWNLOAD_FOLDER_ERROR,
                TransferStatus.LOCAL_FILE_ERROR,
                TransferRejectReason.FILE_READ_ERROR
            }:
                color = (ttk.TTkColor.BOLD + ttk.TTkColor.RED + ttk.TTkColor.BLINKING)

            self.status = value
            value = self.get_translated_status(value)

        if color is None:
            color = ttk.TTkColor.RST

        # Hack the new value into the existing string object of the model
        self.data(column)._text, self.data(column)._colors = ttk.TTkString._parseAnsi(value, color=color)

        if emit:
            self.emitDataChanged()

    @staticmethod
    def get_translated_status(value):
        return STATUSES.get(value, value)


class FileItem(_TransferItem):
    """Row for displaying information about a single Transfer() in the tree."""

    __slots__ = ("transfer", "percent", "_queue_position_data", "_size_data", "_speed_data",
                 "_time_elapsed_data", "_time_left_data")

    def __init__(self, basename, transfer, **kwargs):

        # Keep a reference to the live raw values in the core transfer
        self.transfer = transfer

        # Store raw values for comparing changed data when updating
        self._size_data = self.transfer.size or 0
        self.percent = self.get_percent()
        # self.status = self.get_modified_status()  # values[3]
        self._queue_position_data = self.transfer.queue_position or 0
        self._speed_data = self.transfer.speed or 0
        self._time_elapsed_data = self.transfer.time_elapsed or 0
        self._time_left_data = self.transfer.time_left or 0

        # Transform the raw values into formatted strings for the TreeItem()
        super().__init__([
            ttk.TTkString(basename, ttk.TTkColor.BOLD),  # 0
            f"{self.get_hsize():>20}",   # 1
            f"  {self.percent:3d}%",     # 2
            self.get_modified_status(),  # 3
            self.get_hqueue_position(),  # 4
            self.get_hspeed(),           # 5
            self.get_helapsed(),         # 6
            self.get_hleft()             # 7
        ], **kwargs)

    def setData(self, column, value, color=None, emit=True):
        """Change one of the values in an existing row from raw data"""

        if value is None:
            # TODO: can the value actually ever be None?
            pass  # return

        if column == TransferColumn.SIZE:
            # Caution: Slow, don't update current bytes value too often
            self._size_data = value
            value = f"{self.get_hsize():>20}"

        elif column == TransferColumn.PERCENT:
            if self.percent == value:
                return

            self.percent = value
            # self.parent().update_folder_row()

            value = f"  {value:3d}%"

        elif column == TransferColumn.STATUS:
            if self.status == value:
                return

            self.parent().update_folder_row()
            # super will make translated_status

        elif column == TransferColumn.QUEUE:
            if self._queue_position_data == value:
                return

            self._queue_position_data = value
            value = self.get_hqueue_position()

        elif column == TransferColumn.SPEED:
            if self._speed_data == value:
                return

            self._speed_data = value
            value = self.get_hspeed()

        elif column == TransferColumn.TIME_ELAPSED:
            if self._time_elapsed_data == value:
                return

            self._time_elapsed_data = value
            value = self.get_helapsed()

        elif column == TransferColumn.TIME_LEFT:
            if self._time_left_data == value:
                return

            self._time_left_data = value
            value = self.get_hleft()

        # Hack the new value into the existing string object of the model
        super().setData(column, value, color=color, emit=emit)

    def sortData(self, column):
        """Get the raw value to be used for correct sorting"""

        if column == TransferColumn.NAME:
            pass

        if column == TransferColumn.SIZE:
            return self.transfer.size or 0

        if column == TransferColumn.PERCENT:
            return self.get_percent()

        if column == TransferColumn.STATUS:
            return self.get_modified_status()

        if column == TransferColumn.QUEUE:
            return self.transfer.queue_position or 0

        if column == TransferColumn.SPEED:
            return self.transfer.speed or 0

        if column == TransferColumn.TIME_ELAPSED:
            return self.transfer.time_elapsed or 0

        if column == TransferColumn.TIME_LEFT:
            return self.transfer.time_left or 0

        return str(self.data(column)).lower()  # super().sortData  # natural sort order

    def get_modified_status(self):

        status = self.transfer.status or ""

        if self.transfer.modifier and status == TransferStatus.QUEUED:
            # Priority status
            status += f" ({self.transfer.modifier})"

        return status

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

    # def name(self):
    #     return self.transfer.virtual_path  # str(self.data(TransferColumn.NAME))

    def update_file_row(self):
        """Change the values in an existing row when transfer data changed."""

        is_changed = False
        modified_status = self.get_modified_status()  # + " (prioritized)" etc
        percent = self.get_percent()

        if self.percent != percent or self._size_data != self.transfer.size:
            self.setData(TransferColumn.SIZE, self.transfer.size, emit=False)
            self.setData(TransferColumn.PERCENT, percent, emit=False)
            is_changed = True

        if self.status != modified_status:
            self.setData(TransferColumn.STATUS, modified_status, emit=False)  # super will make translated_status
            is_changed = True

        if self._queue_position_data != self.transfer.queue_position:
            self.setData(TransferColumn.QUEUE, self.transfer.queue_position, emit=False)
            is_changed = True

        if self._speed_data != self.transfer.speed:
            self.setData(TransferColumn.SPEED, self.transfer.speed, emit=False)
            is_changed = True

        if self._time_elapsed_data != self.transfer.time_elapsed:
            self.setData(TransferColumn.TIME_ELAPSED, self.transfer.time_elapsed, emit=False)
            self.setData(TransferColumn.TIME_LEFT, self.transfer.time_left, emit=False)
            is_changed = True

        if is_changed and self.parent().isExpanded():
            self.emitDataChanged()


class FolderItem(_TransferItem):
    """Parent row for containing multiple FileItem() rows inside a folder."""

    def __init__(self, folder_path, **kwargs):

        self.folder_path = folder_path

        super().__init__([self.get_hname(), "", "", "", "", "", "", ""], expanded=True, **kwargs)

        self.files_done = 0
        self.file_items = {}

    def setData(self, column, value, color=None, emit=True):

        if column == TransferColumn.SIZE:
            value = f'{value} File' if value == 1 else f'{value} {_("Files")}'
            color = ttk.TTkColor.ITALIC  # + ttk.TTkColor.fg("#C4C4C4")

        elif column == TransferColumn.PERCENT:
            # if self.files_done == value and self.data(column):
            #     return

            self.files_done = value

            value = f"{value}/{len(self.file_items)}"  # f"  {value:3d}%"
            color = ttk.TTkColor.ITALIC

        super().setData(column, value, color=color, emit=emit)

    def sortData(self, column):

        if column == TransferColumn.NAME:
            return self.folder_path

        if column == TransferColumn.SIZE:
            return len(self.file_items)

        if column == TransferColumn.PERCENT:
            # return self.get_percent()
            return (100 * self.files_done) // len(self.file_items)

        return str(self.data(column)).lower()

    def get_done(self):
        return sum(1 for file_item in self.file_items.values() if file_item.percent >= 100)

    def get_hname(self):
        folder_parents, last_seperator, folder_name = self.folder_path.rpartition("\\")
        share_name, first_seperator, _subfolders = folder_parents.partition("\\")
        dots = "." * folder_parents.count("\\")
        return f"{share_name}{(f'{first_seperator}{dots}' if first_seperator else '')}{last_seperator}{folder_name}"

    # def name(self):
    #     return self.folder_path  # str(self.data(TransferColumn.NAME))

    def add_file_row(self, basename, transfer):
        """Creates a FileItem() and adds an iterator for it."""

        self.file_items[basename] = file_item = FileItem(basename, transfer, parent=self)  # , **kwargs)

        self.update_folder_row()
        self.parent().files_count += 1
        self.parent().update_user_row()

        return file_item

    def take_file_item(self, file_item):

        old_file_item = self.takeChild(self.children().index(file_item))
        del self.file_items[str(file_item.data(TransferColumn.NAME))]  # basename

        self.update_folder_row()
        self.parent().files_count -= 1
        self.parent().update_user_row()

        return old_file_item

    def update_folder_row(self):
        self.setData(TransferColumn.SIZE, len(self.file_items))  # , emit=False)
        self.setData(TransferColumn.PERCENT, self.get_done())  # , emit=self.parent().isExpanded())


class UserItem(_TransferItem):
    """Parent row containing one level of FolderItem() rows under a user."""

    def __init__(self, username, **kwargs):

        self.username = username

        super().__init__([self.get_hname(), "", "", "", "", "", "", ""], **kwargs)

        self.files_count = 0
        self.files_done = 0
        # self.total_file_size = 0
        self.folder_items = {}

    def setData(self, column, value, color=None, emit=True):

        if column == TransferColumn.NAME:
            status, is_buddy = value
            self._data[column] = self.get_hname(status=status, is_buddy=is_buddy)
            # self.emitDataChanged()
            return

        if column == TransferColumn.SIZE:
            value = f'{value} {_("Folder")}' if value == 1 else f'{value} {_("Folders")}'

            # if not self.isExpanded():
            if self.files_count == 1:
                value = f'{self.files_count} File in {value}'
            else:
                value = f'{self.files_count} {_("Files")} in {value}'

            color = ttk.TTkColor.BOLD + ttk.TTkColor.ITALIC  # + ttk.TTkColor.fg("#C4C4C4")

        elif column == TransferColumn.PERCENT:
            # if self.files_done == value and self.data(column):
            #     return

            self.files_done = value

            value = f"{value}/{self.files_count}"  # f"  {value:3d}%"
            color = ttk.TTkColor.ITALIC

        super().setData(column, value, color=color, emit=emit)

    def sortData(self, column):

        if column == TransferColumn.NAME:
            return self.username.lower()

        if column == TransferColumn.SIZE:
            return (self.files_count, len(self.folder_items))

        if column == TransferColumn.PERCENT:
            # return self.get_percent()
            return (100 * self.files_done) // self.files_count

        return str(self.data(column)).lower()

    def name(self):
        return self.username

    def get_done(self):
        return sum(folder_item.files_done for folder_item in self.folder_items.values())

    def get_hname(self, status=None, is_buddy=None):

        status = status or core.users.statuses.get(self.username, None)  # UserStatus.OFFLINE)  # not watched
        is_buddy = is_buddy if is_buddy is not None else (self.username in core.buddies.users)

        username_style = (USERNAME_STYLE + ttk.TTkColor.UNDERLINE) if is_buddy else (USERNAME_STYLE)
        brackets_style = (ttk.TTkColor.BG_WHITE + ttk.TTkColor.MAGENTA) if is_buddy else (ttk.TTkColor.RST)

        return ttk.TTkString(
            f"[{self.username}]", username_style + USER_STATUS_COLORS.get(status)
        ).setColorAt(0, brackets_style).setColorAt(len(self.username) + 2 - 1, brackets_style)

    def add_folder_row(self, folder_path):
        """Creates a FolderItem() and adds an iterator for it."""

        self.folder_items[folder_path] = folder_item = FolderItem(folder_path, parent=self)  # , **kwargs)

        # self.setData(TransferColumn.SIZE, len(self.folder_items))

        return folder_item

    def take_folder_item(self, folder_item):

        if folder_item.file_items:
            # return None
            raise IndexError(f'Cannot remove non-empty tree item "{str(self.data(TransferColumn.NAME))}" '
                             f'({len(folder_item.file_items)} items)')

        old_folder_item = self.takeChild(self.children().index(folder_item))
        del self.folder_items[folder_item.folder_path]

        self.update_user_row()

        return old_folder_item

    def update_user_row(self):
        self.setData(TransferColumn.SIZE, len(self.folder_items))  # , emit=False)
        self.setData(TransferColumn.PERCENT, self.get_done())  # , emit=True)


class TransfersTree(Tree):
    """Root tree containing UserItem parent rows with FolderItem and FileItem
    children, normally known as the 'Group by User' view mode, it is the only
    transfers view layout that is available in the terminal user interface."""

    def __init__(self, parent=None, **kwargs):
        super().__init__(
            parent=parent,
            header=[
                f'   {_("User")} ▹ {_("Folder")} ▹ {_("File Name")}',  # 0
                _("Size"),          # 1
                _("Percent"),       # 2
                _("Status"),        # 3
                _("Queue"),         # 4
                _("Speed"),         # 5
                _("Time Elapsed"),  # 6
                _("Time Left")      # 7
            ],
            **kwargs
        )
        self.module = self.parentWidget().parentWidget().parentWidget()  # Transfers()

        # Column Index               0*  1   2   3  4   5   6   7   8   9  10
        for col, width in enumerate([54, 20, 7, 18, 8, 12, 12, 12]):
            self.setColumnWidth(col, width)

        self.user_items = {}
        self.popup_menu = None

        self.itemActivated.connect(self.on_item_activated)

    def add_user_row(self, username):
        """Creates a UserItem() and adds an iterator for it."""

        self.user_items[username] = user_item = UserItem(
            username, expanded=(config.sections["transfers"][f"expand_{self.module.name()}"] != "none")  # , **kwargs)
        )
        self.addTopLevelItem(user_item)

        return user_item

    def take_user_item(self, user_item):

        if user_item.folder_items:
            # return None
            raise IndexError(f'Cannot remove non-empty tree item "{str(self.data(TransferColumn.NAME))}" '
                             f'({len(user_item.folder_items)} items)')  # DEBUG

        old_user_item = self.takeTopLevelItem(self.indexOfTopLevelItem(user_item))
        del self.user_items[user_item.username]

        return old_user_item

    def clear(self):
        """Removes all items from the list and clears the iterators."""
        for user_item in self.user_items.values():
            for folder_item in user_item.children():
                for file_item in folder_item.children():
                    file_item.heightChanged.clear()
                    file_item._sizeChanged.clear()
                    file_item.transfer = None
                folder_item.heightChanged.clear()
                folder_item._sizeChanged.clear()
                folder_item.takeChildren()
                folder_item.file_items.clear()
            user_item.heightChanged.clear()
            user_item._sizeChanged.clear()
            user_item.takeChildren()
            user_item.folder_items.clear()
        self.invisibleRootItem().takeChildren()
        self.user_items.clear()
        super().clear()

    def mouseEvent(self, evt):

        ret = super().mouseEvent(evt)  # if len(self.selectedItems()) <= 1 else None
        item = None

        if evt.evt == ttk.TTkK.Press:
            if self.popup_menu is not None:
                # Destroy the old menu to dismiss it
                self.popup_menu.close()

            item = self.itemAt(evt.y)

            if item is None:
                if evt.y:
                    self.clearSelection()
                return True

        if item is not None and evt.key == ttk.TTkK.RightButton:
            if item not in self.selectedItems():  # and len(self.selectedItems()) >= 2:
                self.selectItem(item)

            # Create a new menu with actions for all selected file items and parent users
            self.popup_menu = FilePopupMenu(
                self, list(self.get_selected_file_transfers()), closed_callback=self.on_popup_closed
            )
            self.popup_menu.setup_users_menus(set(self._get_parent_user_items(self.selectedItems())))
            self.popup_menu.popup(evt.x, evt.y)
            return True

        return ret  # super().mouseEvent(evt)

    def on_popup_closed(self):
        self.popup_menu = None

    @ttk.pyTTkSlot(FileItem, int)
    def on_item_activated(self, item, _col):

        if not isinstance(item, FileItem):
            # Expand/Collapse UserItem or FolderItem
            return

        self.module.activate_transfer(item.transfer)

    def select_user_file_items(self, selected_user_item):

        # for file_item in self._get_child_file_items([selected_user_item,]):
        #     self.selectItem(file_item)

        for folder_item in selected_user_item.children():
            for file_item in folder_item.children():
                self.selectItem(file_item)

            folder_item.setExpanded(True)

        selected_user_item.setExpanded(True)

    def _get_child_file_items(self, items):
        """Yield all child FileItems under the selected tree items."""

        for item in items:
            if isinstance(item, FileItem):
                yield item

            elif isinstance(item, FolderItem):
                yield from item.children()

            elif isinstance(item, UserItem):
                for folder_item in item.children():
                    yield from folder_item.children()

    def _get_parent_user_items(self, items):
        """Yield all parent UserItems of the selected tree items."""

        for item in items:
            if isinstance(item, FileItem):
                yield item.parent().parent()

            elif isinstance(item, FolderItem):
                yield item.parent()

            elif isinstance(item, UserItem):
                yield item

    def get_selected_file_transfers(self, select_users=False):
        """Yield all core file transfer references in selected tree items."""

        if select_users:
            for user_item in set(self._get_parent_user_items(self.selectedItems())):
                for file_item in self._get_child_file_items(user_item.children()):
                    yield file_item.transfer
        else:
            for file_item in set(self._get_child_file_items(self.selectedItems())):
                yield file_item.transfer


class Transfers(ttk.TTkContainer):

    def __init__(self, screen, name=None):
        super().__init__(layout=ttk.TTkVBoxLayout(), name=name)

        self.screen = screen

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        self.header_bar.layout().addWidget(ttk.TTkSpacer())
        self.users_button = ttk.TTkButton(
            parent=self.header_bar, text=f'0 {_("Users")}', toolTip=_("Collapse All"), minWidth=10, maxWidth=18
        )
        self.users_button.clicked.connect(self.on_collapse_all)
        self.header_bar.layout().addWidget(ttk.TTkSpacer(maxWidth=5))
        self.files_button = ttk.TTkButton(
            parent=self.header_bar, text=f'0 {_("Files")}', toolTip=_("Expand All"), minWidth=10, maxWidth=18
        )
        self.files_button.clicked.connect(self.on_expand_all)
        self.header_bar.layout().addWidget(ttk.TTkSpacer())

        self._spacer = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout(), visible=True)
        _place_top = ttk.TTkSpacer(parent=self._spacer)
        _place_title = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN, text=screen.TAB_LABELS[name]
        )
        self.placeholder = ttk.TTkLabel(
            parent=self._spacer, enabled=False, alignment=ttk.TTkK.CENTER_ALIGN
        )
        _place_bottom = ttk.TTkSpacer(parent=self._spacer)

        self.content = ttk.TTkContainer(parent=self, layout=ttk.TTkVBoxLayout(), visible=False)
        self.tree_container = ttk.TTkContainer(parent=self.content, layout=ttk.TTkVBoxLayout())

        buttons_bar = ttk.TTkContainer(parent=self.content, layout=ttk.TTkHBoxLayout(), maxHeight=1)
        self.buttons_left = ttk.TTkContainer(parent=buttons_bar, layout=ttk.TTkHBoxLayout())
        _buttons_center = ttk.TTkContainer(parent=buttons_bar, layout=ttk.TTkHBoxLayout())
        self.buttons_right = ttk.TTkContainer(parent=buttons_bar, layout=ttk.TTkHBoxLayout())

        self.num_files = 0
        # self.transfer_list = {}
        # self.initialized = False

    def destroy(self):
        self.users_button.clicked.disconnect(self.on_collapse_all)
        self.files_button.clicked.disconnect(self.on_expand_all)
        self.tree.itemActivated.disconnect(self.tree.on_item_activated)
        self.tree.clear()
        self.tree.close()
        # self.close()

    def focus_default_widget(self):

        if self.content.isVisible():
            self.tree.setFocus()
        else:
            self.users_button.setFocus()

    def on_tab_switched(self):
        ttk.TTkHelper.hideCursor()
        self.focus_default_widget()
        self.screen.tab_bar.remove_tab_changed(self)
        # self.update_model()

    def on_collapse_all(self):
        self.tree.collapseAll()
        self.update_expand_state("none")

    def on_expand_all(self):
        self.tree.expandAll()
        self.update_expand_state("all")

    def update_expand_state(self, state):
        config.sections["transfers"][f"expand_{self.name()}"] = state
        config.write_configuration()

    def init_transfers(self, transfer_list):

        # self.transfer_list = transfer_list

        for transfer in transfer_list:
            self.update_specific(transfer)

            # folder_item.setExpanded(True)
            # user_item.setExpanded(True)

        # self.tree.expandAll()

        # self.initialized = True

        self.update_num_users_files()

    def update_num_users_files(self):

        # num_files = 0
        # for user_item in self.tree.user_items.values():
        #     for folder_item in user_item.folder_items.values():
        #         num_files += len(folder_item.file_items)

        self.files_button.setText(f'{self.num_files} {_("Files")}')
        self.users_button.setText(f'{len(self.tree.user_items)} {_("Users")}')

    def update_model(self, transfer, update_parent=True):

        # if self.screen.tab_bar.currentWidget() != self:
        #     if transfer is not None and transfer.iterator is None:
        #         # self.window.notebook.request_tab_changed(self.transfer_page)
        #         transfer.iterator = self.PENDING_ITERATOR_ADD

        #    # No need to do unnecessary work if transfers are not visible
        #    return

        # has_disabled_sorting = False
        # has_selected_parent = False
        # update_counters = False
        # use_reverse_file_path = config.sections["ui"]["reverse_file_paths"]

        if self.update_specific(transfer):
            if self.screen.tab_bar.currentWidget() != self:
                _tab_changed = self.screen.tab_bar.request_tab_changed(self)

            self.update_num_users_files()

        if update_parent:  # and transfer.iterator is not None:
            pass
            # file_item = transfer.iterator
            # folder_item = file_item.parent()
            # user_item = folder_item.parent()

            # folder_item.update_folder_row()
            # user_item.update_user_row()

    def update_specific(self, transfer, select_parent=False):  # , use_reverse_file_path=True):

        # file_item = transfer.iterator

        # Modify old transfer
        # if file_item:  # and iterator not in self.PENDING_ITERATORS:
        #     file_item.update_file_row()
        #     return False

        # current_byte_offset = transfer.current_byte_offset or 0
        # queue_position = transfer.queue_position

        # translated_status = self.translate_status(status)
        # size = transfer.size
        # speed = transfer.speed
        # elapsed = transfer.time_elapsed
        # left = transfer.time_left

        # expand_allowed = self.initialized
        # expand_user = False
        # expand_folder = False
        # user_iterator = None
        # user_folder_path_iterator = None
        # parent_iterator = None
        # select_iterator = None

        # user = transfer.username
        # original_folder_path = folder_path = self.get_transfer_folder_path(transfer)
        # is_sensitive = (status != TransferStatus.USER_LOGGED_OFF)
        # username_underline_data = Pango.Underline.SINGLE if user in core.buddies.users else Pango.Underline.NONE

        # if use_reverse_file_path:
        #     parts = folder_path.split("\\")
        #     parts.reverse()
        #     folder_path = "\\".join(parts)

        # Show tree widget and hide placeholder description
        if not self.tree.user_items:
            self._spacer.setVisible(False)
            self.content.setVisible(True)

        user_item = self.tree.user_items.get(transfer.username, None)

        # Create parent user root item node if it doesn't exist
        if user_item is None:
            user_item = self.tree.add_user_row(transfer.username)

        folder_path, _separator, basename = transfer.virtual_path.rpartition("\\")
        folder_item = user_item.folder_items.get(folder_path, None)

        # Create parent subfolder item node if it doesn't exist
        if folder_item is None:
            folder_item = user_item.add_folder_row(folder_path)

        file_item = folder_item.file_items.get(basename, None)

        # Modify old transfer row if it already exists
        if file_item is not None:  # and iterator not in self.PENDING_ITERATORS:
            file_item.update_file_row()
            return False

        # Transfer row doesn't exist yet, create new file item
        file_item = folder_item.add_file_row(basename, transfer)
        self.num_files += 1

        # transfer.iterator = file_item
        # self.row_id += 1

        if select_parent:
            _selected_items = self.tree.selectedItems()

            if len(_selected_items) != 1 and user_item not in _selected_items:
                # Select parent row of newly added transfer, and scroll to it.
                # Unselect any other rows to prevent accidental actions on
                # previously selected transfers.
                self.tree.clearSelection()
                self.tree.selectItem(user_item)

        return True

    def clear_transfer(self, transfer, update_parent=True):

        # file_item = transfer.iterator
        # transfer.iterator = None

        # if not file_item:
        #     return

        # folder_item = file_item.parent()
        # user_item = folder_item.parent()
        user_item = self.tree.user_items.get(transfer.username)

        if user_item is None:
            return

        folder_path, _separator, basename = transfer.virtual_path.rpartition("\\")
        folder_item = user_item.folder_items.get(folder_path)

        if folder_item is None:
            return

        file_item = folder_item.file_items.get(basename)

        if file_item is None:
            return

        # Remove file row
        _old_file_item = folder_item.take_file_item(file_item)
        self.num_files -= 1
        old_folder_item = None

        # Remove folder row if empty
        if not folder_item.file_items:
            old_folder_item = user_item.take_folder_item(folder_item)

        # Remove user row if empty
        if not user_item.folder_items:
            self.tree.take_user_item(user_item)

        elif update_parent:
            if old_folder_item is None:
                pass  # folder_item.update_folder_row()

            # user_item.update_user_row()

        # TODO: Avoid updating label during batch updates
        self.update_num_users_files()

        if not self.tree.user_items:
            self.content.setVisible(False)
            self._spacer.setVisible(True)

    def abort_transfer(self, transfer, status_message=None, update_parent=True):
        if status_message is not None and status_message != TransferStatus.QUEUED:
            self.update_model(transfer, update_parent=update_parent)

    def update_buddy(self, user, user_data=None):

        user_item = self.tree.user_items.get(user, None)

        if user_item is None:
            return

        if user_data is not None:
            status = user_data.status
            is_buddy = True
        else:
            status = None
            is_buddy = False

        user_item.setData(TransferColumn.NAME, (status, is_buddy))

    def user_status(self, msg):

        user_item = self.tree.user_items.get(msg.user, None)

        if user_item is None:
            return

        user_item.setData(TransferColumn.NAME, (msg.status, None))  # (status, is_buddy)

    def activate_transfer(self, transfer):

        action = config.sections["transfers"][f"{self.name()}_doubleclick"]

        if self.screen.application.isolated_mode and action in {1, 2}:
            # External applications not available in isolated_mode mode
            return

        if action == 1:    # Open File
            self.open_files([transfer,])

        elif action == 2:  # Open in File Manager
            self.open_file_manager([transfer,])

        elif action == 3:  # Search
            pass  # self.on_search_filename() ##

        elif action == 4:  # Pause / Abort
            self.abort_selected_transfers([transfer,])

        elif action == 5:  # Remove
            self.remove_selected_transfers([transfer,])

        elif action == 6:  # Resume / Retry
            self.retry_selected_transfers([transfer,])

        elif action == 7:  # Browse Folder
            self.browse_folder(transfer)

    def select_user_transfers(self, username):

        user_item = self.tree.user_items.get(username, None)

        if user_item is None:
            return

        self.tree.clearSelection()
        self.tree.select_user_file_items(user_item)

    def user_profile(self, selected_user_items):
        for user_item in selected_user_items:
            core.userinfo.show_user(user_item.username)

    def open_files(self, selected_transfers):
        # Implemented in subclasses
        raise NotImplementedError

    def open_file_manager(self, selected_transfers):
        # Implemented in subclasses
        raise NotImplementedError

    def browse_folder(self, selected_transfer):
        # Implemented in subclasses
        raise NotImplementedError

    def retry_selected_transfers(self, selected_transfers):
        # Implemented in subclasses
        raise NotImplementedError

    def abort_selected_transfers(self, selected_transfers):
        # Implemented in subclasses
        raise NotImplementedError

    def remove_selected_transfers(self, selected_transfers):
        # Implemented in subclasses
        raise NotImplementedError

    def on_retry_transfer(self, *_args):
        self.retry_selected_transfers(self.tree.get_selected_file_transfers())

    def on_abort_transfer(self, *_args):
        self.abort_selected_transfers(self.tree.get_selected_file_transfers())

    def on_remove_transfer(self, *_args):
        self.remove_selected_transfers(self.tree.get_selected_file_transfers())
