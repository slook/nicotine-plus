# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

#from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.widgets.pages import Pages


class Interests(ttk.TTkSplitter):

    def __init__(self, screen, name="interests"):
        super().__init__(name=name)

        self.screen = screen

        self.header = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        _expander_left = ttk.TTkSpacer(parent=self.header)

        self.interests_title = ttk.TTkLabel(
            parent=self.header, alignment=ttk.TTkK.CENTER_ALIGN,
            text=ttk.TTkString(self.screen.TAB_LABELS[name], ttk.TTkColor.BOLD)
            #minWidth=5, maxWidth=5
        )

        _expander_right = ttk.TTkSpacer(parent=self.header)

        self.personal_frame = ttk.TTkFrame(layout=ttk.TTkVBoxLayout(), title=_("Personal Interests"))
        self.recommendations_frame = ttk.TTkFrame(layout=ttk.TTkVBoxLayout(), title=_("Recommendations"))
        self.similar_frame = ttk.TTkFrame(layout=ttk.TTkVBoxLayout(), title=_("Similar Users"))

        self.likes_list_container = ttk.TTkFrame(parent=self.personal_frame, layout=ttk.TTkVBoxLayout(), border=True)
        self.hates_list_container = ttk.TTkFrame(parent=self.personal_frame, layout=ttk.TTkVBoxLayout(), border=True)

        self.likes_list_view = ttk.TTkTree(parent=self.likes_list_container, header=[_("Likes")])
        self.hates_list_view = ttk.TTkTree(parent=self.hates_list_container, header=[_("Dislikes")])

        self.addWidget(
            self.personal_frame, size=min(self.screen.width() // 4, len(self.personal_frame.title()) + 8)
        )
        self.addWidget(self.recommendations_frame)
        self.addWidget(self.similar_frame)

        for event_name, callback in (
            #("add-dislike", self.add_thing_i_hate),
            #("add-interest", self.add_thing_i_like),
            #("global-recommendations", self.global_recommendations),
            #("item-recommendations", self.item_recommendations),
            #("item-similar-users", self.item_similar_users),
            #("recommendations", self.recommendations),
            #("remove-dislike", self.remove_thing_i_hate),
            #("remove-interest", self.remove_thing_i_like),
            #("server-login", self.server_login),
            #("server-disconnect", self.server_disconnect),
            #("similar-users", self.similar_users),
            #("user-country", self.user_country),
            #("user-stats", self.user_stats),
            #("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def connect_signals(self):
        self.screen.tab_bar.currentChanged.connect(self.on_focus_tab)

    def focus_default_widget(self):
        self.likes_list_view.setFocus()

    @ttk.pyTTkSlot(int)
    def on_focus_tab(self, _tab_number):
        if self.screen.tab_bar.currentWidget() == self:
            self.screen.setWidget(widget=self.header, position=self.screen.HEADER)
            self.focus_default_widget()
