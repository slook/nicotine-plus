# MIT License
#
# Copyright (c) 2021 Eugenio Parodi <ceccopierangiolieugenio AT googlemail DOT com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__all__ = ['TTkFileTreeWidget']

import os
import datetime
import stat

from TermTk.TTkCore.color import TTkColor

from TermTk.TTkCore.constant import TTkK
from TermTk.TTkCore.cfg import TTkCfg
from TermTk.TTkCore.string import TTkString
from TermTk.TTkWidgets.TTkModelView.treewidget import TTkTreeWidget
from TermTk.TTkWidgets.TTkModelView.filetreewidgetitem import TTkFileTreeWidgetItem
from TermTk.TTkCore.signal import pyTTkSlot, pyTTkSignal

class TTkFileTreeWidget(TTkTreeWidget):
    '''
    A :py:class:`TTkFileTreeWidget` provide a widget that allow users to select files or directories.

    The :py:class:`TTkFileTree` class enables a user to traverse the file system in order to select one or many files or a directory.

    ::

        Name                                 ▼╿Size         ╿Type        ╿Date Modified       ╿▲
         ∙ Makefile                           │      3.80 KB│File        │2024-11-04 20:37:22 │┊
         ∙ README.md                          │      7.50 KB│File        │2024-06-08 15:34:09 │┊
         - TermTk/                            │             │Folder      │2024-06-08 15:34:12 │┊
           + TTkAbstract/                     │             │Folder      │2024-11-04 20:37:22 │▓
           + TTkCore/                         │             │Folder      │2024-11-04 20:37:22 │▓
           + TTkCrossTools/                   │             │Folder      │2024-06-08 15:34:12 │▓
           + TTkGui/                          │             │Folder      │2024-11-04 20:37:22 │▓
           + TTkLayouts/                      │             │Folder      │2024-11-04 20:37:22 │▓
           - TTkTemplates/                    │             │Folder      │2024-11-04 20:37:22 │┊
             ∙ __init__.py                    │    120 bytes│File        │2024-11-04 20:37:22 │┊
             + __pycache__/                   │             │Folder      │2024-11-05 08:47:38 │┊
             ∙ dragevents.py                  │      2.79 KB│File        │2024-11-04 20:37:22 │┊
             ∙ keyevents.py                   │      2.52 KB│File        │2024-11-04 20:37:22 │┊
             ∙ mouseevents.py                 │      5.16 KB│File        │2024-11-04 20:37:22 │┊
           + TTkTestWidgets/                  │             │Folder      │2024-11-04 20:37:22 │┊
           + TTkTheme/                        │             │Folder      │2024-06-08 15:34:12 │┊
           + TTkTypes/                        │             │Folder      │2024-06-08 15:34:12 │┊
           + TTkUiTools/                      │             │Folder      │2024-11-04 20:37:22 │┊
           + TTkWidgets/                      │             │Folder      │2024-11-04 20:37:22 │┊
           ∙ __init__.py                      │    327 bytes│File        │2024-11-04 19:56:26 │▼

    Quickstart:

    .. code-block:: python

        import TermTk as ttk

        root = ttk.TTk(layout=ttk.TTkGridLayout())

        fileTree = ttk.TTkFileTree(parent=root, path='.')

        root.mainloop()
    '''

    @property
    def fileClicked(self) -> pyTTkSignal:
        '''
        This signal is emitted when a file is clicked

        :param file:
        :type  file: :py:class:`TTkFileTreeWidgetItem`
        '''
        return self._fileClicked
    @property
    def folderClicked(self) -> pyTTkSignal:
        '''
        This signal is emitted when a folder is clicked

        :param folder:
        :type  folder: :py:class:`TTkFileTreeWidgetItem`
        '''
        return self._folderClicked
    @property
    def fileDoubleClicked(self) -> pyTTkSignal:
        '''
        This signal is emitted when a file is doubleclicked

        :param file:
        :type  file: :py:class:`TTkFileTreeWidgetItem`
        '''
        return self._fileDoubleClicked
    @property
    def folderDoubleClicked(self) -> pyTTkSignal:
        '''
        This signal is emitted when a folder is doubleclicked

        :param folder:
        :type  folder: :py:class:`TTkFileTreeWidgetItem`
        '''
        return self._folderDoubleClicked
    @property
    def fileActivated(self) -> pyTTkSignal:
        '''
        This signal is emitted when a file is activated

        :param file:
        :type  file: :py:class:`TTkFileTreeWidgetItem`
        '''
        return self._fileActivated
    @property
    def folderActivated(self) -> pyTTkSignal:
        '''
        This signal is emitted when a fiilder is activated

        :param folder:
        :type  folder: :py:class:`TTkFileTreeWidgetItem`
        '''
        return self._folderActivated

    __slots__ = ('_path', '_filter',
                 # Signals
                 '_fileClicked', '_folderClicked', '_fileDoubleClicked', '_folderDoubleClicked', '_fileActivated', '_folderActivated')
    def __init__(self,
                 path:str='.',
                 **kwargs) -> None:
        '''
        :param path: the starting path opened by the :py:class:`TTkFileTreeWidget`, defaults to the current path ('.')
        :type  path: str, optional
        '''
        # Signals
        self._fileClicked         = pyTTkSignal(TTkFileTreeWidgetItem)
        self._folderClicked       = pyTTkSignal(TTkFileTreeWidgetItem)
        self._fileDoubleClicked   = pyTTkSignal(TTkFileTreeWidgetItem)
        self._folderDoubleClicked = pyTTkSignal(TTkFileTreeWidgetItem)
        self._fileActivated       = pyTTkSignal(TTkFileTreeWidgetItem)
        self._folderActivated     = pyTTkSignal(TTkFileTreeWidgetItem)
        self._path   = path
        self._filter = '*'
        super().__init__(**kwargs)
        self.setHeaderLabels(["Name", "Size", "Type", "Date Modified"])
        self.setColumnWidth(0, 40)
        self._sortingEnabled = True
        self.sortItems(0, self._sortOrder)

        self.openPath(self._path)
        #self.resizeColumnToContents(0)
        self.resizeColumnToContents(1)
        self.resizeColumnToContents(2)
        self.resizeColumnToContents(3)
        self.itemExpanded.connect(self._updateChildren)
        self.itemActivated.connect(self._activated)

    def sortKey(self, item):

        def _dirsTop():
            # Always group dirs above files regardless of order
            isDir = item.getType() == TTkFileTreeWidgetItem.DIR
            return isDir if self._sortOrder == TTkK.DescendingOrder else (not isDir)

        # Sort by _raw data values, and also sub-sort by Name (0) as tie-breaker
        return (_dirsTop(), item.sortData(self._sortColumn), item.sortData(0))

    def setFilter(self, filter):
        self._filter = filter
        # TODO: Avoid to refer directly '_rootItem'
        TTkFileTreeWidgetItem.setFilter(self._rootItem, filter)

    def getOpenPath(self):
        return self._path

    def openPath(self, path):
        if not os.path.exists(path): return
        self._path = path

        # Temporarily disable sorting for increased performance
        isSorted = self._sortingEnabled
        self._sortingEnabled = False

        self.clear()
        self.addTopLevelItems(TTkFileTreeWidget._getFileItems(path))
        self.setFilter(self._filter)

        self.setSortingEnabled(isSorted)
        self.sortItems(self._sortColumn, self._sortOrder)

    @staticmethod
    def _getFileItems(path):
        path = os.path.abspath(path)

        def _getSize(fsize):
            if fsize <= 0:
                return ""
            if fsize > (1024*1024*1024):
                return f"{fsize/(1024*1024*1024):.2f} GB"
            if fsize > (1024*1024):
                return f"{fsize/(1024*1024):.2f} MB"
            if fsize > 1024:
                return f"{fsize/1024:.2f} KB"
            return f"{fsize} B"  # bytes

        def _getTime(mtime):
            if not mtime: return ""
            return datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')

        def _getItem(entry):
            #nodePath = entry.path
            st = None

            try:
                st = entry.stat()  # follow_symlinks=False)

            except OSError as error:
                # Error reading file entry
                time, size, rawTime, rawSize = "", "", 0, 0
                color = TTkCfg.theme.failNameColor
                name = TTkString()+color+entry.name
                typef="Broken"

            if entry.is_dir():
                rawTime = st.st_mtime if st else 0
                time = _getTime(rawTime)
                rawSize = -1
                size = ""
                color = TTkCfg.theme.folderNameColor
                item_type = TTkFileTreeWidgetItem.DIR
                item_indicator = TTkK.ShowIndicator
                ext = ""

                if entry.is_symlink():
                    name = TTkString()+TTkCfg.theme.linkNameColor+entry.name+os.sep+TTkColor.RST+' -> '+color+os.readlink(entry.path).rstrip(os.sep)+os.sep
                    typef = "Folder Link"
                else:
                    name = TTkString()+color+entry.name.rstrip(os.sep)+os.sep
                    typef = "Folder"

            elif entry.is_file():  # follow_symlinks=False  # or entry.is_symlink():
                rawTime = st.st_mtime if st else 0
                time = _getTime(rawTime)
                rawSize = st.st_size if st else 0
                size = _getSize(rawSize)
                item_type = TTkFileTreeWidgetItem.FILE
                item_indicator = TTkK.DontShowIndicator

                _, ext = os.path.splitext(entry.name)
                if ext: ext = ext.lstrip(".")

                if bool(st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                    color = TTkCfg.theme.executableColor
                    typef="File (Exec)"
                else:
                    color = TTkCfg.theme.fileNameColor
                    typef="File"  # (.{ext})"

                if entry.is_symlink():
                    name = TTkString()+TTkCfg.theme.linkNameColor+entry.name+TTkColor.RST+' -> '+color+os.readlink(entry.path)
                    typef += " Link"
                else:
                    name = TTkString()+color+entry.name

            else:
                time, size, rawTime, rawSize = "", "", 0, 0
                color = TTkCfg.theme.failNameColor
                name = TTkString()+color+entry.name
                typef, ext = "Invalid", ""

            return TTkFileTreeWidgetItem(
                [ name, size, typef, time],
                raw = [ entry.name , rawSize , ext , rawTime ],
                path=entry.path,
                type=item_type,
                childIndicatorPolicy=item_indicator)

        ret = []

        try:
            with os.scandir(path) as entries:
                for entry in entries:
                    ret.append(_getItem(entry))

        except OSError as error:
            # Folder doesn't exist or error reading folder
            pass

        return ret

    @pyTTkSlot(TTkFileTreeWidgetItem)
    def _updateChildren(self, item):
        if item.children(): return
        item.addChildren(children := TTkFileTreeWidget._getFileItems(item.path()))
        for i in children:
            # TODO: Find a better way than calling an internal function
            i._processFilter(self._filter)
        if not self._sortingEnabled: return
        item.sortChildren(self._sortColumn, self._sortOrder, key=self.sortKey)

    @pyTTkSlot(TTkFileTreeWidgetItem, int)
    def _activated(self, item, _):
        path = item.path()
        if os.path.isdir(path):
            self.folderActivated.emit(item)
        elif os.path.isfile(path):
            self.fileActivated.emit(item)