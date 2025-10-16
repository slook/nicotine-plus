# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os

import TermTk as ttk

from pynicotine.ttktui.widgets.options import Box
from pynicotine.utils import open_folder_path


class FileChooserButton(ttk.TTkFileButtonPicker):
    def __init__(self, *args, callback=None, caption="", padding=(0, 1, 1, 1), parent=None, path=None, label_text="",
                 show_open_external_button=True, end_button=None, **kwargs):

        container = Box(parent=parent, padding=padding, label_text=label_text)
        super().__init__(*args, parent=container, caption=caption, **kwargs)

        self.open_external_button = None
        self.default_path_button = None

        self.callback = callback
        self.default_path = path

        if path is not None:
            self.set_path(path)

        if not self.caption():
            self.setCaption(_("Select a Folder") if self.fileMode() == ttk.TTkK.FileMode.Directory else _("Save as…"))

        if show_open_external_button:
            self.open_external_button = ttk.TTkButton(
                parent=container, text="⌼", toolTip=_("Open in File Manager"), maxWidth=3
            )
            self.open_external_button.clicked.connect(self.on_open_external)

        if self.fileMode() == ttk.TTkK.FileMode.Directory:
            if path is not None:
                self.default_path_button = ttk.TTkButton(text="↺", toolTip=_("Default"), maxWidth=3)
                self.default_path_button.clicked.connect(self.on_default_path)
                container.layout().addWidget(self.default_path_button)  # ttk.TTkButton(parent=container, text=""

            self.setFilter(f"Folders (*{os.sep});;All Files (*)")
            self.folderPicked.connect(self.on_path_picked)
        else:
            pass  # TODO

        # if end_button is not None:
        #     self.layout().addWidget(end_button)

    def destroy(self):

        if self.open_external_button is not None:
            self.open_external_button.clicked.disconnect(self.on_open_external)
            self.open_external_button.close()
            self.open_external_button = None

        if self.default_path_button is not None:
            self.default_path_button.clicked.disconnect(self.on_default_path)
            self.default_path_button.close()
            self.default_path_button = None

        self.callback = self.default_path = None
        self.folderPicked.disconnect(self.on_path_picked)
        self.set_path("")

        self.parentWidget().close()  # Box container
        self.close()
        self.__dict__.clear()

    def get_path(self):
        return self.path()

    def set_path(self, path):
        # More lenient solution than os.path.basename() to avoid empty strings
        self.setText(path.rstrip(os.sep).rpartition(os.sep)[-1] or path)
        self.setPath(os.path.expandvars(path.rstrip(os.sep)))
        self.setToolTip(self.path())  # Show path without env variables

    @ttk.pyTTkSlot()
    def on_default_path(self):
        if self.fileMode() == ttk.TTkK.FileMode.Directory:
            self.on_path_picked(self.default_path)

    @ttk.pyTTkSlot(str)
    def on_path_picked(self, path):

        self.set_path(path)

        if self.callback is not None:
            self.callback(self.path())  # callback_data=

    @ttk.pyTTkSlot()
    def on_open_external(self):
        path = os.path.expandvars(self.path())
        folder_path = (path if self.fileMode() == ttk.TTkK.FileMode.Directory else os.path.dirname(path))
        open_folder_path(folder_path, create_folder=True)
