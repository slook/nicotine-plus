# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import sys

import TermTk as ttk

import pynicotine
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.widgets.dialogs import Dialog
from pynicotine.ttktui.widgets.theme import NICOTINE_ICON_COLOR
from pynicotine.ttktui.widgets.theme import URL_COLOR


class About(Dialog):

    def __init__(self, application):
        super().__init__(
            parent=application.screen,
            show_callback=self.on_show,
            close_callback=self.on_close,
            title=_("About"),
            width=60,
            height=30
        )

        #nicotine_icon = ttk.TTkImage(rasteriser=ttk.TTkImage.HALFBLOCK)
        ##data = ttk.TTkUtil.base64_deflate_2_obj(NICOTINE_ICON)
        #nicotine_icon.setData(str(NICOTINE_ICON))
        #nicotine_icon.setMinimumSize(16,8)
        #nicotine_icon.setMaximumWidth(16)
        #self.main_icon = ttk.TTkContainer(layout=ttk.TTkHBoxLayout())
        #self.main_icon.layout().addWidget(ttk.TTkSpacer())
        #self.main_icon.layout().addWidget(nicotine_icon)
        #self.main_icon.layout().addWidget(ttk.TTkSpacer())

        self.application_version_label = ttk.TTkLabel(
            text=f"{pynicotine.__application_name__} {pynicotine.__version__}",
            color=ttk.TTkColor.BOLD + NICOTINE_ICON_COLOR,
            alignment=ttk.TTkK.CENTER_ALIGN
        )
        self.dependency_versions_label = ttk.TTkLabel(
            text=f"TTk {ttk.__version__}   •   Python {sys.version.split()[0]}", alignment=ttk.TTkK.CENTER_ALIGN
        )
        self.status_label = ttk.TTkLabel(text="", alignment=ttk.TTkK.CENTER_ALIGN, visible=False)
        self.website_label = ttk.TTkLabel(
            text=ttk.TTkString(
                pynicotine.__website_url__,
                ttk.TTkColor.fg(config.sections["ui"].get("urlcolor", "#5288CE"), link=pynicotine.__website_url__)
            ),
            alignment=ttk.TTkK.CENTER_ALIGN
        )
        self.copyright_label = ttk.TTkLabel(
            text=pynicotine.__copyright__, color=ttk.TTkColor.ITALIC, alignment=ttk.TTkK.CENTER_ALIGN
        )
        self.copyright_label.setMinimumHeight(4)

        self.is_version_outdated = False
        events.connect("check-latest-version", self.on_check_latest_version)

    def on_show(self, window):

        for label_widget in (
            #self.main_icon,
            self.application_version_label,
            self.dependency_versions_label,
            self.status_label,
            self.website_label,
            self.copyright_label
        ):
            window.layout().addWidget(ttk.TTkSpacer(minHeight=1))
            window.layout().addWidget(label_widget)

        if core.update_checker is None:
            # Update checker is not loaded
            return

        if self.is_version_outdated:
            # No need to check latest version again
            return

        self.status_label.setText(
            ttk.TTkString(_("Checking latest version…")) + ttk.TTkString("…", ttk.TTkColor.BLINKING)
        )
        self.status_label.setToolTip("")
        self.status_label.setVisible(True)

        core.update_checker.check()

    def on_check_latest_version(self, latest_version, is_outdated, error):

        if error:
            icon = ttk.TTkString("🛇", ttk.TTkColor.BOLD + ttk.TTkColor.RED)
            message = _("Error checking latest version: %s") % f"\n{error}"
            self.status_label.setToolTip(error)

        elif is_outdated:
            icon = ttk.TTkString("🛆", ttk.TTkColor.BOLD + ttk.TTkColor.YELLOW + ttk.TTkColor.BLINKING)
            message = _("New release available: %s") % latest_version

        else:
            icon = ttk.TTkString("✅", ttk.TTkColor.BOLD + ttk.TTkColor.GREEN)
            message = _("Up to date")

        self.is_version_outdated = is_outdated
        self.status_label.setText(icon + ttk.TTkString(" " + message))

    def on_close(self, _window):
        self.parent.focus_default_widget()
