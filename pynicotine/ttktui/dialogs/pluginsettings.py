# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
# from pynicotine.gtkgui.application import GTK_API_VERSION
# from pynicotine.gtkgui.widgets.combobox import ComboBox
from pynicotine.ttktui.widgets.dialogs import Dialog
from pynicotine.ttktui.widgets.options import CheckBox
from pynicotine.ttktui.widgets.options import DropDownListBox
from pynicotine.ttktui.widgets.options import EntryBox
from pynicotine.ttktui.widgets.options import SpinBox
# from pynicotine.gtkgui.widgets.dialogs import EntryDialog
# from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
# from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
# from pynicotine.gtkgui.widgets.textview import TextView
# from pynicotine.gtkgui.widgets.theme import add_css_class


class PluginSettings(Dialog):

    def __init__(self, application):

        self.plugin_name = None
        self.plugin_metasettings = None
        self.option_widgets = {}
        self.group_containers = {}

        self.scroll_area = ttk.TTkScrollArea()  # horizontalScrollBarPolicy=ttk.TTkK.ScrollBarAlwaysOff)
        self.primary_container = ttk.TTkContainer(parent=self.scroll_area.viewport(), paddingLeft=1)  # paddingRight=0)
        self.primary_layout = ttk.TTkVBoxLayout()

        self.buttons_box = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), paddingLeft=1, paddingRight=1, maxHeight=3)
        self.cancel_button = ttk.TTkButton(parent=self.buttons_box, text=_("_Cancel"), border=True)
        self.cancel_button.clicked.connect(self.on_cancel)
        _buttons_spacer = ttk.TTkSpacer(parent=self.buttons_box)
        self.ok_button = ttk.TTkButton(parent=self.buttons_box, text=_("_Apply"), border=True)
        self.ok_button.clicked.connect(self.on_ok)

        super().__init__(
            parent=application._instance,  # screen,  # preferences.window,
            content_box=self.scroll_area,
            buttons_box=self.buttons_box,
            default_widget=self.ok_button,
            show_callback=self.on_show,
            close_callback=self.on_close,
            width=60,
            height=30,
            modal=True
            # show_title_buttons=False
        )
        self.content_box.sizeChanged.connect(self.on_resize)

    def destroy(self):

        self.content_box.sizeChanged.disconnect(self.on_resize)

        for button in {self.cancel_button, self.ok_button}:
            button.clicked.clear()
            button.close()

        for widget in self.option_widgets.values():
            if isinstance(widget, ttk.TTkTree):
                # widget.popup_menu.destroy()
                widget.clear()
                widget.close()

        for frame in self.group_containers.values():
            frame.close()

        self.option_widgets.clear()
        self.group_containers.clear()
        # self.__dict__.clear()

    def _generate_group_container(self, group):

        if not group:
            group = ""

        if group in self.group_containers:
            return self.group_containers[group]

        group_container = self.group_containers[group] = ttk.TTkFrame(
            layout=ttk.TTkVBoxLayout(), title=group, titleAlign=ttk.TTkK.LEFT_ALIGN
        )
        group_container.layout().addWidget(ttk.TTkSpacer(minHeight=1))

        self.primary_layout.addWidget(group_container)
        self.primary_layout.addWidget(ttk.TTkSpacer(minHeight=1))

        return group_container

    def _add_options(self):

        self.option_widgets.clear()
        self.group_containers.clear()

        self.primary_layout.clear()
        self.primary_layout = ttk.TTkVBoxLayout()

        for option_name, data in self.plugin_metasettings.items():
            option_type = data.get("type")

            if not option_type:
                continue

            description = data.get("description", "")
            group = data.get("group")
            option_value = config.sections["plugins"][self.plugin_name.lower()][option_name]

            group_container = self._generate_group_container(group)
            widget = None

            if option_type == "bool":
                widget = CheckBox(checked=option_value, text=description)

            elif option_type == "dropdown":
                widget = DropDownListBox(label_text=description, items=data.get("options", []))
                widget.set_selected_id(option_value)

            elif option_type in {"str", "string"}:
                widget = EntryBox(label_text=description, text=option_value)

            elif option_type in {"integer", "int", "float"}:
                widget = SpinBox(
                    label_text=description,
                    value=option_value, minimum=data.get("minimum", 0), maximum=data.get("maximum", 99999),
                    # stepsize=data.get("stepsize", 1), decimals=(0 if option_type in {"integer", "int"} else 2)
                )

            else:
                widget = ttk.TTkLabel(text=f"Option type '{option_type}' not implemented: {option_name}={option_value}")

            self.option_widgets[option_name] = widget
            group_container.layout().addWidget(widget.parentWidget() or widget)  # Box container

    @staticmethod
    def _get_widget_data(widget):

        if isinstance(widget, CheckBox):
            return widget.get_active()

        if isinstance(widget, DropDownListBox):
            return widget.get_selected_id()

        if isinstance(widget, EntryBox):
            return widget.get_text()

        if isinstance(widget, SpinBox):
            return widget.get_value_as_int()

    def load_options(self, plugin_name, plugin_metasettings):

        self.plugin_name = plugin_name
        self.plugin_metasettings = plugin_metasettings

        self._add_options()

    def on_show(self, window):

        plugin_human_name = core.pluginhandler.get_plugin_human_name(self.plugin_name)
        window.setTitle(_("%s Settings") % plugin_human_name)

        # self.on_resize(self.content_box.width(), self.content_box.height())
        self.primary_container.setLayout(self.primary_layout)

    def on_close(self, window):
        self.scroll_area.viewport().viewMoveTo(0, 0)

    @ttk.pyTTkSlot(int, int)
    def on_resize(self, w: int, h: int):
        self.primary_container.setGeometry(
            0, 0,
            max(w - 1, self.primary_layout.minimumWidth()), self.primary_layout.minimumHeight() - 1
        )

    @ttk.pyTTkSlot()
    def on_cancel(self):
        self.close()

    @ttk.pyTTkSlot()
    def on_ok(self):

        plugin = core.pluginhandler.enabled_plugins[self.plugin_name]

        for option_name in self.plugin_metasettings:
            new_value = self._get_widget_data(self.option_widgets[option_name])

            if new_value is not None:
                plugin.settings[option_name] = new_value

        self.close()
