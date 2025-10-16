# SPDX-FileCopyrightText: 2025-2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.ttktui.widgets.menus import UserPopupMenu
from pynicotine.ttktui.widgets.theme import USER_STATUS_ICONS
from pynicotine.ttktui.widgets.theme import USER_STATUS_LABELS
from pynicotine.utils import human_speed


class _Item(ttk.TTkTreeWidgetItem):
    pass


class Tree(ttk.TTkTree):
    class Item(_Item):
        pass


class _UserItem(_Item):

    def __init__(self, data, **kwargs):
        """Create a row that will later be added to a list"""

        # Store the raw values
        self.status = data[0]
        #self.username = str(data[1])  # get raw _text value from TTkString without color codes
        self.files = data[2]

        # Transform the raw values into formatted strings
        data[0] = USER_STATUS_LABELS.get(self.status, "")
        data[2] = f"{self.files:8d}" if self.files is not None else ""  # humanize(self.files)
        #data[4] = ""  # data[4] = f"{human_speed(self.speed):>12}" if self.speed > 0 else ""
        #data[5] = f"{self.folders:8d}"  # humanize(self.folders)

        super().__init__(data, icon=USER_STATUS_ICONS.get(self.status), **kwargs)

        #self._alignment = [ttk.TTkK.LEFT_ALIGN, ttk.TTkK.LEFT_ALIGN, ttk.TTkK.RIGHT_ALIGN, ttk.TTkK.RIGHT_ALIGN]
        #self.setTextAlignment(2, ttk.TTkK.RIGHT_ALIGN)
        #self.setTextAlignment(4, ttk.TTkK.RIGHT_ALIGN)

        #self.username = data[1]

    def name(self):
        return str(self.data(1))  # self.username  # get raw _text value from TTkString without color codes

    def setData(self, column, value, emit=True):
        """Change one of the values in an existing row from raw data"""

        if column == 0:
            if value is None or value == self.status:
                return
            self.status = value
            value = USER_STATUS_LABELS.get(self.status, "")

        elif column == 2:
            if value is None or value == self.files:
                return
            self.files = value
            value = f"{self.files:8d}"  # humanize(self.files)

        # Hack the new value into the existing string object of the model
        self.data(column)._text, self.data(column)._colors = ttk.TTkString._parseAnsi(str(value))

        if column == 0:
            # Setting the icon causes a signal the data changed
            self.setIcon(0, USER_STATUS_ICONS.get(self.status))

        elif emit:
            self.emitDataChanged()

    def sortData(self, column):
        """Define the raw value to be used for correct sorting"""

        if column == 2:
            return self.files or 0

        return str(self.data(column)).lower()


class UsersList(Tree):

    _KEY_COLUMN = 1  # ("User")
    _SORT_COLUMN = 1
    _SORT_ORDER = ttk.TTkK.AscendingOrder

    class UserItem(_UserItem):
        # Override this to use a custom TTkTreeWidgetItem() for drawing the rows
        pass

    def __init__(self,
        parent=None,
        header=[
            " ",            # 0 status
            _("User"),      # 1 _KEY_COLUMN
            _("Files"),     # 2
            _("Country"),   # 3
            #_("Speed"),    # 4
            #_("Folders"),  # 5
        ],
        **kwargs
    ):

        self.iterators = {}  # Reference to each UserItem() by name
        self.popup_menu = None

        if parent is None:
            # Global room doesn't have a user list
            return

        super().__init__(
            parent=parent,
            header=header,
            name=parent.name(),
            **kwargs
        )
        #self.setTextAlignment(2, ttk.TTkK.RIGHT_ALIGN)
        #self.setTextAlignment(4, ttk.TTkK.RIGHT_ALIGN)
        self.sortItems(self._SORT_COLUMN, self._SORT_ORDER)

        for col, width in enumerate([3, 30, 8]):
            self.setColumnWidth(col, width)

        self.itemActivated.connect(self.on_user_item_activated)

    def clear(self):
        """Removes all items from the list and clears the iterators"""
        self.iterators.clear()
        super().clear()

    def add_rows(self, rows):
        """Creates multiple UserItem() from a list of lists and adds them to
        the iterators. This method avoids individually painting each row."""

        new_user_items = {str(data[self._KEY_COLUMN]): self.UserItem(data) for data in rows}

        self.addTopLevelItems(list(new_user_items.values()))

        self.iterators.update(new_user_items)

    def add_row(self, data):  # , iterator_key=None):  # , **kwargs):
        """Creates a UserItem() from a list of values and adds an iterator"""

        self.iterators[str(data[self._KEY_COLUMN])] = user_item = self.UserItem(data)  # , **kwargs)

        self.addTopLevelItem(user_item)

        return user_item

    def mouseEvent(self, evt):

        ret = super().mouseEvent(evt)

        if evt.evt == ttk.TTkK.Press:
            if self.popup_menu is not None:
                # Destroy the old menu to dismiss it
                self.popup_menu.close()
                self.popup_menu = None

            if evt.key == ttk.TTkK.RightButton:
                user_item = self.itemAt(evt.y)

                if user_item is None:
                    # Blank area (y>len) or header (y=0)
                    return False

                # Create a new menu with actions for this user item
                #self.popup_menu = UserPopupMenu(self, str(user_item.data(self._KEY_COLUMN)))
                self.popup_menu = UserPopupMenu(self, user_item)
                self.popup_menu.popup(evt.x, evt.y)
                return True

        return ret
