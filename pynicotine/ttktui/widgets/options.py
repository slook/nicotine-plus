# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk


class Box(ttk.TTkContainer):

    def __init__(self, *args, padding=(0, 1, 1, 1), label_text="", **kwargs):
        super().__init__(*args, layout=ttk.TTkHBoxLayout(), padding=padding, **kwargs)
        if label_text:
            self.layout().addWidget(ttk.TTkLabel(text=label_text))
            self.layout().addWidget(ttk.TTkSpacer(maxWidth=1))


class CheckBox(ttk.TTkCheckBox):

    def __init__(self, *args, padding=(0, 1, 1, 1), parent=None, label_text="", **kwargs):
        box = Box(parent=parent, padding=padding, label_text=label_text)
        super().__init__(*args, parent=box, **kwargs)

    def get_active(self):
        return self.isChecked()

    def set_active(self, is_active):
        is_changed = (self.isChecked() != is_active)
        self.setChecked(is_active)
        if not is_changed:
            self.toggled.emit(is_active)


class DropDownListBox(ttk.TTkComboBox):

    def __init__(self, *args, padding=(0, 1, 1, 1), parent=None, container=None, label_text="", items=[], **kwargs):

        self._ids = {}
        self._positions = {}
        _list = []

        for position, item in enumerate(items):
            if isinstance(item, str):
                item_text, item_id = item, item
            else:
                item_text, item_id = item

            self._ids[position] = item_id
            self._positions[item_id] = position
            _list.append(item_text)

        box = container or Box(parent=parent, padding=padding, label_text=label_text,
                               minWidth=(len(label_text) + max(len(item_text) for item_text in _list or ["",]) + 12))

        super().__init__(*args, parent=box, list=_list, **kwargs)  # editable=False

    def get_selected_id(self):
        item_id = self._ids.get(self.currentIndex())
        return item_id

    def set_selected_id(self, item_id):
        position = self._positions.get(item_id, -1)
        self.setCurrentIndex(position)

    def get_text(self):
        return self.currentText()

    def set_text(self, text):
        self.setCurrentText(text or "")


class EntryBox(ttk.TTkLineEdit):

    def __init__(self, *args, padding=(0, 1, 1, 1), parent=None, label_text="", **kwargs):
        box = Box(parent=parent, padding=padding, label_text=label_text, minWidth=(len(label_text) + 12))
        super().__init__(*args, parent=box, **kwargs)

    def get_text(self):
        return str(self.text())

    def set_text(self, text):
        self.setText(text)


class ListBox(ttk.TTkList):

    def __init__(self, *args, parent=None, title="", **kwargs):
        frame = ttk.TTkFrame(parent=parent, layout=ttk.TTkHBoxLayout(), title=title)
        # box = Box(parent=parent, padding=padding, label_text=label_text, minWidth=(len(label_text) + 12))
        super().__init__(*args, parent=frame, **kwargs)


class SpinBox(ttk.TTkSpinBox):

    def __init__(self, *args, maxWidth=12, padding=(0, 1, 1, 1), parent=None, label_text="", **kwargs):
        box = Box(parent=parent, padding=padding, label_text=label_text, minWidth=(len(label_text) + 15))
        super().__init__(*args, parent=box, maxWidth=maxWidth, **kwargs)

    def get_value_as_int(self):
        return int(self.value())

    def set_value(self, value):
        self.setValue(value)
