# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
#from pynicotine.gtkgui.application import GTK_API_VERSION
#from pynicotine.gtkgui.widgets.combobox import ComboBox
from pynicotine.ttktui.widgets.dialogs import Dialog
#from pynicotine.gtkgui.widgets.dialogs import EntryDialog
#from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
#from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
#from pynicotine.gtkgui.widgets.textview import TextView
#from pynicotine.gtkgui.widgets.theme import add_css_class


class PluginSettings(Dialog):

    def __init__(self, application):

        self.application = application
        self.plugin_name = None
        self.plugin_metasettings = None
        self.option_widgets = {}

        self.scroll_area = ttk.TTkScrollArea()  # horizontalScrollBarPolicy=ttk.TTkK.ScrollBarAlwaysOff)
        self.primary_container = ttk.TTkContainer(parent=self.scroll_area.viewport())
        self.primary_layout = ttk.TTkVBoxLayout()

        self.buttons_box = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), paddingLeft=1, paddingRight=1, maxHeight=3)
        self.cancel_button = ttk.TTkButton(parent=self.buttons_box, text=_("_Cancel"), border=True)
        self.cancel_button.clicked.connect(self.on_cancel)
        _buttons_spacer = ttk.TTkSpacer(parent=self.buttons_box)
        self.ok_button = ttk.TTkButton(parent=self.buttons_box, text=_("_Apply"), border=True)
        self.ok_button.clicked.connect(self.on_ok)

        super().__init__(
            parent=application.preferences.window,
            content_box=self.scroll_area,
            buttons_box=self.buttons_box,
            #default_button=ok_button,
            show_callback=self.on_show,
            close_callback=self.on_close,
            width=60,
            height=30,
            modal=True
            #show_title_buttons=False
        )

    def destroy(self):

        for widget in self.option_widgets.values():
            if isinstance(widget, ttk.TTkTree):
                #widget.popup_menu.destroy()
                widget.clear()
                widget.close()

        self.option_widgets.clear()
        self.__dict__.clear()

    def _add_boolean_option(self, option_name, option_value, description):

        container = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), padding=(0, 1, 1, 1))

        return ttk.TTkCheckbox(parent=container, text=description)

    def _add_dropdown_option(self, option_name, option_value, description, items):

        container = ttk.TTkContainer(
            layout=ttk.TTkHBoxLayout(),
            padding=(0, 1, 1, 1),
            minWidth=(len(description) + max(len(item) for item in items) + 32)
        )
        container.layout().addWidget(ttk.TTkLabel(text=description))

        return ttk.TTkComboBox(parent=container, list=items)

    def _add_entry_option(self, option_name, option_value, description):

        container = ttk.TTkContainer(
            layout=ttk.TTkHBoxLayout(),
            padding=(0, 1, 1, 1),
            minWidth=(len(description) + 32)
        )
        container.layout().addWidget(ttk.TTkLabel(text=description))

        return ttk.TTkLineEdit(parent=container)

    def _add_numerical_option(self, option_name, option_value, description, minimum, maximum, stepsize, decimals):

        max_len = max(len(str(maximum)), len(str(option_value))) + 2
        container = ttk.TTkContainer(
            layout=ttk.TTkHBoxLayout(),
            padding=(0, 1, 1, 1),
            minWidth=(len(description) + max_len + 8)
        )
        container.layout().addWidget(ttk.TTkLabel(text=description))

        return ttk.TTkSpinBox(parent=container, minimum=minimum, maximum=maximum, maxWidth=max_len)

    def _add_options(self):

        self.option_widgets.clear()
        self.primary_layout.clear()
        self.primary_layout = ttk.TTkVBoxLayout()
        self.primary_layout.addWidget(ttk.TTkSpacer(minHeight=1))

        for option_name, data in self.plugin_metasettings.items():
            option_type = data.get("type")

            if not option_type:
                continue

            description = data.get("description", "")
            option_value = config.sections["plugins"][self.plugin_name.lower()][option_name]

            if option_type == "bool":
                self.option_widgets[option_name] = widget = self._add_boolean_option(
                    option_name, option_value, description)

            elif option_type == "dropdown":
                self.option_widgets[option_name] = widget = self._add_dropdown_option(
                    option_name, option_value, description, items=data.get("options", []))

            elif option_type in {"str", "string"}:
                self.option_widgets[option_name] = widget = self._add_entry_option(
                    option_name, option_value, description)

            elif option_type in {"integer", "int", "float"}:
                self.option_widgets[option_name] = widget = self._add_numerical_option(
                    option_name, option_value, description, minimum=data.get("minimum", 0),
                    maximum=data.get("maximum", 99999), stepsize=data.get("stepsize", 1),
                    decimals=(0 if option_type in {"integer", "int"} else 2)
                )

            else:
                self.option_widgets[option_name] = None
                continue

            self.application.preferences.set_widget(widget, option_value)
            self.primary_layout.addWidget(widget.parentWidget())

    @staticmethod
    def _get_widget_data(widget):

        if isinstance(widget, ttk.TTkCheckbox):
            return widget.isChecked()

        if isinstance(widget, ttk.TTkComboBox):
            return str(widget.currentText())

        if isinstance(widget, ttk.TTkLineEdit):
            return str(widget.text())

        if isinstance(widget, ttk.TTkSpinBox):
            return widget.value()


    def load_options(self, plugin_name, plugin_metasettings):

        self.plugin_name = plugin_name
        self.plugin_metasettings = plugin_metasettings

        self._add_options()

    def on_show(self, window):

        plugin_human_name = core.pluginhandler.get_plugin_info(self.plugin_name).get("Name", self.plugin_name)
        window.setTitle(_("%s Settings") % plugin_human_name)

        self.primary_container.setGeometry(*self.primary_layout.fullWidgetAreaGeometry())
        self.primary_container.setLayout(self.primary_layout)
        self.scroll_area.viewport().viewChanged.emit()  # show scrollbar if needed

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

    def on_close(self, window):
        self.scroll_area.viewport().viewMoveTo(0, 0)
