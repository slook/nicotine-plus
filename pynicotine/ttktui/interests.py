# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.slskmessages import UserStatus
from pynicotine.ttktui.chatrooms import UsersList
from pynicotine.ttktui.widgets.menus import PopupMenu
from pynicotine.ttktui.widgets.trees import UsersList
from pynicotine.utils import human_speed
#from pynicotine.utils import humanize


class Interests(ttk.TTkSplitter):

    def __init__(self, screen, name="interests"):
        super().__init__(name=name)

        self.screen = screen

        self.header_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), minHeight=1)

        _expander_left = ttk.TTkSpacer(parent=self.header_bar)

        self.interests_title = ttk.TTkLabel(
            parent=self.header_bar, alignment=ttk.TTkK.CENTER_ALIGN,
            text=ttk.TTkString(self.screen.TAB_LABELS[name], ttk.TTkColor.BOLD)
        )

        _expander_right = ttk.TTkSpacer(parent=self.header_bar)

        self.populated_recommends = False

        self.interests_picker = InterestsPicker(editable=True, recommend_callback=self.show_item_recommendations)
        self.interests_picker.populate_interests(
            likes=[like for like in config.sections["interests"]["likes"] if isinstance(like, str)],
            hates=[hate for hate in config.sections["interests"]["dislikes"] if isinstance(hate, str)]
        )

        self.recommendations_browser = RecommendationsBrowser(recommend_callback=self.show_item_recommendations)
        self.recommendations_browser.recommendations_button.menuButtonClicked.connect(self.on_refresh_recommendations)
        self.similar_users_viewer = SimilarUsersViewer()

        self.view_splitter = ttk.TTkSplitter(name=name)
        self.view_splitter.layout().addWidget(self.recommendations_browser)
        self.view_splitter.layout().addWidget(self.similar_users_viewer)
        self.view_splitter.sizeChanged.connect(self.on_view_resize)
        self.similar_users_viewer.orientation_button.menuButtonClicked.connect(self.on_view_orientation)

        self.layout().addWidget(self.interests_picker)
        self.layout().addWidget(self.view_splitter)

        self.setSizes([min(self.screen.width() // 4, 40), None])
        self.view_splitter.setSizes([self.screen.width() // 4 + 10, self.screen.width() // 2])

        for event_name, callback in (
            ("add-dislike", self.add_thing_i_hate),
            ("add-interest", self.add_thing_i_like),
            ("global-recommendations", self.global_recommendations),
            ("item-recommendations", self.item_recommendations),
            ("item-similar-users", self.item_similar_users),
            ("recommendations", self.recommendations),
            ("remove-dislike", self.remove_thing_i_hate),
            ("remove-interest", self.remove_thing_i_like),
            ("server-login", self.server_login),
            ("server-disconnect", self.server_disconnect),
            ("similar-users", self.similar_users),
            ("user-country", self.user_country),
            ("user-stats", self.user_stats),
            ("user-status", self.user_status)
        ):
            events.connect(event_name, callback)

    def destroy(self):
        self.screen.tab_bar.currentChanged.disconnect(self.on_focus_tab)
        self.view_splitter.sizeChanged.disconnect(self.on_view_resize)
        self.similar_users_viewer.orientation_button.menuButtonClicked.disconnect(self.on_view_orientation)
        self.closed.disconnect(self.destroy)

        self.interests_picker.close()
        self.recommendations_browser.recommendations_list.clear()
        self.recommendations_browser.recommendations_list.close()
        self.similar_users_viewer.similar_users_list.clear()
        self.similar_users_viewer.similar_users_list.close()

    def connect_signals(self):
        self.screen.tab_bar.currentChanged.connect(self.on_focus_tab)
        self.closed.connect(self.destroy)

    def focus_default_widget(self):
        self.interests_picker.add_like_entry.setFocus()

    @ttk.pyTTkSlot(int)
    def on_focus_tab(self, _tab_number):
        if self.screen.tab_bar.currentWidget() == self:
            self.screen.setWidget(widget=self.header_bar, position=self.screen.HEADER)
            self.focus_default_widget()
            self.populate_recommendations()

    @ttk.pyTTkSlot(int, int)
    def on_view_resize(self, w, h):

        new_orientation = ttk.TTkK.Direction.VERTICAL if (w / 2) < h else ttk.TTkK.Direction.HORIZONTAL

        if new_orientation == self.view_splitter.orientation():
            return

        self.view_splitter.setOrientation(new_orientation)

        # Workaround for unequal panel sizes
        #self.view_splitter._processRefSizes(self.view_splitter.width(), self.view_splitter.height())
        #self.view_splitter._updateGeometries()

    #@ttk.pyTTkSlot(bool)
    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_view_orientation(self, button):

        self.view_splitter.sizeChanged.disconnect(self.on_view_resize)

        if self.view_splitter.orientation() == ttk.TTkK.Direction.VERTICAL:
            self.view_splitter.setOrientation(ttk.TTkK.Direction.HORIZONTAL)
            button.setText("≑")  # ◫ ⌸ ↹ ⇌ ≓ ≑
        else:
            self.view_splitter.setOrientation(ttk.TTkK.Direction.VERTICAL)
            button.setText("◫")  # ◫ ⌸ ↹ ⇌ ≓ ≑

        # Workaround for unequal panel sizes
        #self.view_splitter._processRefSizes(self.view_splitter.width(), self.view_splitter.height())
        #self.view_splitter._updateGeometries()

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_refresh_recommendations(self, _button):
        self.show_recommendations()

    def server_login(self, msg):

        if not msg.success:
            return

        self.recommendations_browser.recommendations_button.setEnabled(True)

        if self.screen.tab_bar.currentWidget() != self:
            # Only populate recommendations if the tab is open on login
            return

        self.populate_recommendations()

    def server_disconnect(self, *_args):

        self.recommendations_browser.recommendations_button.setEnabled(False)

        for item in self.similar_users_viewer.similar_users_list.invisibleRootItem().children():
            item.setData(0, UserStatus.OFFLINE)

        self.populated_recommends = False

    def populate_recommendations(self):
        """Populates the lists of recommendations and similar users if empty."""

        if self.populated_recommends or core.users.login_status == UserStatus.OFFLINE:
            return

        self.show_recommendations()

    def show_recommendations(self, always_global=False):

        self.recommendations_browser.setTitle("...")
        self.similar_users_viewer.setTitle("...")

        if always_global or (not self.interests_picker.likes_list.invisibleRootItem().children() and
                             not self.interests_picker.hates_list.invisibleRootItem().children()):
            core.interests.request_global_recommendations()
        else:
            core.interests.request_recommendations()

        core.interests.request_similar_users()
        self.populated_recommends = True

    def show_item_recommendations(self, recommend, request_items=True, request_users=True):
        """recommend_callback for InterestsPicker, RecommendationsBrowser and UserInfo"""

        if core.users.login_status == UserStatus.OFFLINE:
            return

        if request_items or not self.populated_recommends:
            self.recommendations_browser.setTitle("...")
            core.interests.request_item_recommendations(recommend)
            self.populated_recommends = True

        if request_users:
            self.similar_users_viewer.setTitle("...")
            core.interests.request_item_similar_users(recommend)

        if self.screen.tab_bar.currentWidget() != self:
            self.screen.tab_bar.setCurrentWidget(self)

    def add_thing_i_like(self, item, select_row=True):

        like = item.strip().lower()

        if not like:
            return

        item = _InterestItem([like])

        if self.interests_picker.likes_list.indexOfTopLevelItem(item) < 0:
            self.interests_picker.likes_list.addTopLevelItem(item)  # , select_row=select_row)

    def add_thing_i_hate(self, item, select_row=True):

        hate = item.strip().lower()

        if not hate:
            return

        item = _InterestItem([hate])

        if self.interests_picker.hates_list.indexOfTopLevelItem(item) < 0:
            self.interests_picker.hates_list.addTopLevelItem(item)  # , select_row=select_row)

    def remove_thing_i_like(self, like):

        for item in self.interests_picker.likes_list.invisibleRootItem().children():
            if str(item.data(0)) != like:
                continue

            index = self.interests_picker.likes_list.indexOfTopLevelItem(item)
            _old_item = self.interests_picker.likes_list.takeTopLevelItem(index)
            return

    def remove_thing_i_hate(self, hate):

        for item in self.interests_picker.hates_list.invisibleRootItem().children():
            if str(item.data(0)) != hate:
                continue

            index = self.interests_picker.hates_list.indexOfTopLevelItem(item)
            _old_item = self.interests_picker.hates_list.takeTopLevelItem(index)
            return

    def global_recommendations(self, msg):
        self.recommendations_browser.set_recommendations(msg.recommendations, msg.unrecommendations, is_global=True)

    def recommendations(self, msg):

        if msg.recommendations or msg.unrecommendations:
            self.recommendations_browser.set_recommendations(msg.recommendations, msg.unrecommendations)
            return

        # No personal recommendations, fall back to global ones
        self.show_recommendations(always_global=True)

    def item_recommendations(self, msg):
        self.recommendations_browser.set_recommendations(msg.recommendations, msg.unrecommendations, msg.thing)

    def similar_users(self, msg):
        self.similar_users_viewer.set_similar_users(msg.users)

    def item_similar_users(self, msg):
        rating = 0
        self.similar_users_viewer.set_similar_users({user: rating for user in msg.users}, msg.thing)

    def user_country(self, user, country_code):

        iterator = self.similar_users_viewer.similar_users_list.iterators.get(user)

        if iterator is None:
            return

        # flag_icon_name = get_flag_icon_name(country_code)
        iterator.setData(5, country_code)

    def user_status(self, msg):

        iterator = self.similar_users_viewer.similar_users_list.iterators.get(msg.user)

        if iterator is None:
            return

        iterator.setData(0, msg.status)

    def user_stats(self, msg):

        iterator = self.similar_users_viewer.similar_users_list.iterators.get(msg.user)

        if iterator is None:
            return

        iterator.setData(4, msg.avgspeed)
        iterator.setData(3, msg.dirs)
        iterator.setData(2, msg.files)

    def minimumHeight(self):
        return 0  # Keep main window status bar on top


class InterestsPicker(ttk.TTkSplitter):

    def __init__(self, editable=False, recommend_callback=None, **kwargs):
        super().__init__(orientation=ttk.TTkK.Direction.VERTICAL, **kwargs)

        self._editable = editable
        self.recommend_callback = recommend_callback

        self.likes_list_container = ttk.TTkFrame(
            layout=ttk.TTkVBoxLayout(), border=True, name="likes",
            title=_("Personal Interests") if editable else _("Interests"),
            titleAlign=ttk.TTkK.LEFT_ALIGN if editable else ttk.TTkK.CENTER_ALIGN
        )
        self.hates_list_container = ttk.TTkFrame(
            layout=ttk.TTkVBoxLayout(), border=True, name="hates",
            title=_("Personal Dislikes") if editable else _("Dislikes"),
            titleAlign=ttk.TTkK.LEFT_ALIGN if editable else ttk.TTkK.CENTER_ALIGN
        )

        if editable:
            self.add_like_container = ttk.TTkContainer(
                parent=self.likes_list_container, layout=ttk.TTkHBoxLayout(), paddingRight=1
            )
            self.add_like_button = ttk.TTkButton(
                parent=self.add_like_container,
                text=ttk.TTkString("😄"),
                minWidth=4, maxWidth=4, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
            )
            self.add_like_entry = ttk.TTkLineEdit(parent=self.add_like_container, hint=_("Add something you like…"))
            self.add_like_entry.returnPressed.connect(self.on_add_thing_i_like)
            self.add_like_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
            self.add_like_button.clicked.connect(self.on_add_thing_i_like)

            self.add_hate_container = ttk.TTkContainer(
                parent=self.hates_list_container, layout=ttk.TTkHBoxLayout(), paddingRight=1
            )
            self.add_hate_button = ttk.TTkButton(
                parent=self.add_hate_container,
                text=ttk.TTkString("😠"),
                minWidth=4, maxWidth=4, addStyle={'default': {'borderColor': ttk.TTkColor.BLACK}}
            )
            self.add_hate_entry = ttk.TTkLineEdit(parent=self.add_hate_container, hint=_("Add something you dislike…"))
            self.add_hate_entry.returnPressed.connect(self.on_add_thing_i_hate)
            self.add_hate_button.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
            self.add_hate_button.clicked.connect(self.on_add_thing_i_hate)
        else:
            self.add_like_container = self.add_hate_container = None

        self.hates_menu_bar = ttk.TTkMenuBarLayout()
        self.orientation_button = self.hates_menu_bar.addMenu("≓", data="auto", alignment=ttk.TTkK.RIGHT_ALIGN)
        self.orientation_button.setToolTip("Panel Orientation")
        self.orientation_button.menuButtonClicked.connect(self.on_orientation)
        self.hates_list_container.setMenuBar(self.hates_menu_bar, position=ttk.TTkK.BOTTOM)

        self.likes_list = _InterestsList(self, parent=self.likes_list_container)  # , name="likes")
        self.hates_list = _InterestsList(self, parent=self.hates_list_container)  # , name="hates")

        self.sizeChanged.connect(self.on_resize)
        self.closed.connect(self.destroy)

        self.layout().addWidget(self.likes_list_container)
        self.layout().addWidget(self.hates_list_container)

    def destroy(self):

        if self.add_like_container is not None:
            self.add_like_entry.returnPressed.disconnect(self.on_add_thing_i_like)
            self.add_hate_entry.returnPressed.disconnect(self.on_add_thing_i_hate)
            self.add_like_button.clicked.disconnect(self.on_add_thing_i_like)
            self.add_hate_button.clicked.disconnect(self.on_add_thing_i_hate)

        self.orientation_button.menuButtonClicked.connect(self.on_orientation)

        self.likes_list.close()
        self.hates_list.close()

        self.sizeChanged.disconnect(self.on_resize)
        self.closed.disconnect(self.destroy)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_orientation(self, button):

        button.setData("manual")

        if self.orientation() == ttk.TTkK.Direction.VERTICAL:
            self.setOrientation(ttk.TTkK.Direction.HORIZONTAL)
            button.setText("≑")  # ◫ ⌸ ↹ ⇌ ≓ ≑ ⎅
        else:
            self.setOrientation(ttk.TTkK.Direction.VERTICAL)
            button.setText("◫")  # ◫ ⌸ ↹ ⇌ ≓ ≑

        # Workaround for unequal panel sizes
        #self._processRefSizes(self.width(), self.height())
        #self._updateGeometries()

        self.likes_list.setColumnWidth(0, self.likes_list.width() - 3)  # w - 5)
        self.hates_list.setColumnWidth(0, self.hates_list.width() - 3)  # w - 5)

    @ttk.pyTTkSlot(int, int)
    def on_resize(self, w, h):

        new_orientation = ttk.TTkK.Direction.HORIZONTAL if 40 < (w / 2) > h else ttk.TTkK.Direction.VERTICAL

        if self.orientation_button.data() == "auto" and self.orientation() != new_orientation:
            self.setOrientation(new_orientation)
            self._processRefSizes(self.width(), self.height())
            self._updateGeometries()

        self.likes_list.setColumnWidth(0, self.likes_list.width() - 3)  # w - 5)
        self.hates_list.setColumnWidth(0, self.hates_list.width() - 3)  # w - 5)

    def clear(self):
        self.likes_list.clear()
        self.hates_list.clear()

    def populate_interests(self, likes=None, hates=None):

        self.clear()

        self.likes_list.addTopLevelItems([_InterestItem([like]) for like in likes])
        self.hates_list.addTopLevelItems([_InterestItem([hate]) for hate in hates])

        if not self._editable:
            num_liked = len([
                like for like in self.likes_list.invisibleRootItem().children() if like._LIKE_ICON in str(like.icon(0))
            ])
            self.likes_list_container.setTitle(f'{len(likes)} {(_("Interests"))} ({num_liked} things in common)')

        self.likes_list.sortItems(0, self.likes_list._treeView._sortOrder)
        self.hates_list.sortItems(0, self.hates_list._treeView._sortOrder)

    @ttk.pyTTkSlot()
    def on_add_thing_i_like(self):

        like = str(self.add_like_entry.text()).strip()

        if not like:
            self.add_like_entry.setFocus()
            return

        self.add_like_entry.setText("")
        core.interests.add_thing_i_like(like)

    @ttk.pyTTkSlot()
    def on_add_thing_i_hate(self):

        hate = str(self.add_hate_entry.text()).strip()

        if not hate:
            self.add_hate_entry.setFocus()
            return

        self.add_hate_entry.setText("")
        core.interests.add_thing_i_hate(hate)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_remove_thing_i_like(self, button):

        like = str(button.data())

        if not like:
            return

        core.interests.remove_thing_i_like(like)
        self.add_like_entry.setFocus()
        button.setData("")

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_remove_thing_i_hate(self, button):

        hate = button.data()

        if not hate:
            return

        core.interests.remove_thing_i_hate(hate)
        self.add_hate_entry.setFocus()
        button.setData("")


class _InterestItem(ttk.TTkTreeWidgetItem):

    _KEY_COLUMN = 0   # 0=("Like" or "Dislike"); 1="Recommendation"
    _LIKE_ICON = "☺"
    _HATE_ICON = "☹"

    def __init__(self, data):

        data[self._KEY_COLUMN] = data[self._KEY_COLUMN].strip().lower()
        icon = None

        if data[self._KEY_COLUMN] in config.sections["interests"]["likes"]:
            icon = self._LIKE_ICON

        elif data[self._KEY_COLUMN] in config.sections["interests"]["dislikes"]:
            icon = self._HATE_ICON

        super().__init__(data, icon=icon)  # , **kwargs)

    @ttk.pyTTkSlot(bool)
    def on_like_recommendation(self, is_liked):
        if is_liked:
            core.interests.add_thing_i_like(str(self.data(self._KEY_COLUMN)))
            self.setIcon(0, self._LIKE_ICON)
        else:
            core.interests.remove_thing_i_like(str(self.data(self._KEY_COLUMN)))
            self.setIcon(0, ttk.TTkCfg.theme.tree[0])

    @ttk.pyTTkSlot(bool)
    def on_hate_recommendation(self, is_hated):
        if is_hated:
            core.interests.add_thing_i_hate(str(self.data(self._KEY_COLUMN)))
            self.setIcon(0, self._HATE_ICON)
        else:
            core.interests.remove_thing_i_hate(str(self.data(self._KEY_COLUMN)))
            self.setIcon(0, ttk.TTkCfg.theme.tree[0])


class _InterestsList(ttk.TTkTree):

    _SORT_COLUMN = 0
    _SORT_ORDER = ttk.TTkK.AscendingOrder

    def __init__(self, interests_picker, parent=None, header=None):
        super().__init__(
            parent=parent,
            header=header or ([_("Likes")] if parent.name() == "likes" else [_("Dislikes")])
        )
        self.sortItems(self._SORT_COLUMN, self._SORT_ORDER)

        self.itemActivated.connect(self.on_recommend_item_activated)
        self.closed.connect(self.destroy)

        self.interests_picker = interests_picker
        self.popup_menu = None

    def destroy(self):

        if self.popup_menu is not None:
            self.popup_menu.close()
            self.popup_menu = None

        self._treeView.setSortingEnabled(False)
        self.itemActivated.disconnect(self.on_recommend_item_activated)
        self.closed.disconnect(self.destroy)
        self.clear()

    def mouseEvent(self, evt):

        ret = super().mouseEvent(evt)

        if evt.evt == ttk.TTkK.Press:
            if self.popup_menu is not None:
                self.popup_menu.close()
                self.popup_menu = None

            if evt.key == ttk.TTkK.RightButton:
                item = self.itemAt(evt.y)

                if item is None:
                    return False

                self.create_popup_menu(item)
                self.popup_menu.popup(evt.x, evt.y)
                return True

        return ret

    def create_popup_menu(self, item):

        recommendation = str(item.data(item._KEY_COLUMN))  # 0="Likes"/"Dislikes"; 1="Item"

        self.popup_menu = PopupMenu(self, title=recommendation)

        if self.parentWidget().name() == "recommendations" or not self.interests_picker._editable:
            self.popup_menu.addMenu(_("I _Like This"), name="like", checkable=True)
            self.popup_menu.addMenu(_("I _Dislike This"), name="hate", checkable=True)
            self.popup_menu.addSpacer()

            self.popup_menu.like.setChecked(recommendation in config.sections["interests"]["likes"])
            self.popup_menu.hate.setChecked(recommendation in config.sections["interests"]["dislikes"])

            self.popup_menu.like.toggled.connect(item.on_like_recommendation)
            self.popup_menu.hate.toggled.connect(item.on_hate_recommendation)

        self.popup_menu.addMenu(_("_Recommendations for Item"), name="recommend_item", data=recommendation)
        self.popup_menu.addMenu(_("_Search for Item"), name="recommend_search", data=recommendation)

        if core.users.login_status != UserStatus.OFFLINE:
            self.popup_menu.recommend_item.menuButtonClicked.connect(self.on_recommend_item)
            self.popup_menu.recommend_search.menuButtonClicked.connect(self.on_recommend_search)
        else:
            self.popup_menu.recommend_item.setEnabled(False)
            self.popup_menu.recommend_search.setEnabled(False)

        if self.parentWidget().name() != "recommendations" and self.interests_picker._editable:
            self.popup_menu.addSpacer()
            self.popup_menu.addMenu("Remove", name="remove_thing", data=recommendation)

            if self.parentWidget().name() == "likes":
                self.popup_menu.remove_thing.menuButtonClicked.connect(self.interests_picker.on_remove_thing_i_like)
            else:
                self.popup_menu.remove_thing.menuButtonClicked.connect(self.interests_picker.on_remove_thing_i_hate)

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_recommend_search(self, button):
        core.search.do_search(button.data(), mode="global")

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_recommend_item(self, button):
        """show_item_recommendations"""
        self.interests_picker.recommend_callback(button.data())

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_recommend_item_activated(self, item, _col):
        """show_item_recommendations for the selected like or hate"""
        self.interests_picker.recommend_callback(str(item.data(item._KEY_COLUMN)))


class RecommendationsBrowser(ttk.TTkFrame):

    def __init__(self, recommend_callback=None):  # , **kwargs):
        super().__init__(
            layout=ttk.TTkVBoxLayout(), border=True, name="recommendations",
            title=_("Recommendations"), titleAlign=ttk.TTkK.LEFT_ALIGN  # , **kwargs
        )

        self._editable = False
        self.recommend_callback = recommend_callback

        self.recommendations_menu_bar = ttk.TTkMenuBarLayout()
        self.recommendations_button = self.recommendations_menu_bar.addMenu(" ↻ ", alignment=ttk.TTkK.RIGHT_ALIGN)
        self.recommendations_button.setEnabled(False)
        self.recommendations_button.setToolTip(_("Refresh Recommendations"))
        self.setMenuBar(self.recommendations_menu_bar)

        self.recommendations_list = _RecommendationsList(self, parent=self)

    def set_recommendations(self, recommendations, unrecommendations, item=None, is_global=False):

        if item:
            self.setTitle(_("Recommendations for %(item)s") % {"item": item})
        else:
            self.setTitle(_("Popular Interests") if is_global else _("Recommendations"))
            unrecommendations.reverse()

        self.recommendations_list.clear()
        self.recommendations_list.addTopLevelItems(
            [_RecommendationItem([rating, thing]) for thing, rating in recommendations + unrecommendations]
        )
        self.recommendations_list.sortItems(
            self.recommendations_list.sortColumn(),
            self.recommendations_list._treeView._sortOrder
        )
        self.recommendations_list.resizeColumnToContents(1)


class _RecommendationItem(_InterestItem):

    _KEY_COLUMN = 1   # ("Item")
    _LIKE_ICON = "☻"

    def __init__(self, data):  # , **kwargs):
        self.rating = data[0]  # sort by int
        data[0] = f"{self.rating:+6d}"  # humanize(self.rating)
        super().__init__(data)

    def sortData(self, col):

        if col == 0:
            return self.rating  # sort by int

        return str(self.data(col))


class _RecommendationsList(_InterestsList):

    _SORT_COLUMN = 0  # ("Rating")
    _SORT_ORDER = ttk.TTkK.DescendingOrder

    def __init__(self, recommendations_browser, parent=None):
        super().__init__(
            recommendations_browser,
            parent=parent,
            header=[f'   {(_("Rating"))}', _("Item")]  # _KEY_COLUMN = 1  # ("Item")
        )
        self.setColumnWidth(0, 12)
        #self.setTextAlignment(0, ttk.TTkK.RIGHT_ALIGN)

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_recommend_item_activated(self, item, _col):
        """Show similar users for the selected recommendation item"""
        self.interests_picker.recommend_callback(str(item.data(item._KEY_COLUMN)), request_items=False)


class SimilarUsersViewer(ttk.TTkFrame):

    def __init__(self):  # , **kwargs):
        super().__init__(
            layout=ttk.TTkVBoxLayout(), border=True,  # name="similar_users",
            title=_("Similar Users"), titleAlign=ttk.TTkK.LEFT_ALIGN  # , **kwargs)
        )

        self.similar_users_menu_bar = ttk.TTkMenuBarLayout()
        self.orientation_button = self.similar_users_menu_bar.addMenu("≓", alignment=ttk.TTkK.RIGHT_ALIGN)
        self.orientation_button.setToolTip("Panel Orientation")
        self.setMenuBar(self.similar_users_menu_bar, position=ttk.TTkK.BOTTOM)

        self.similar_users_list = _SimilarUsersList(parent=self)

    def set_similar_users(self, users, item=None):

        self.setTitle((_("Users who like %(item)s") % {"item": item}) if item else _("Similar Users"))

        self.similar_users_list.clear()
        self.similar_users_list.add_rows((self._generate_user_rows(users)))
        self.similar_users_list.sortItems(
            self.similar_users_list.sortColumn(),
            self.similar_users_list._treeView._sortOrder
        )
        self.similar_users_list.resizeColumnToContents(5)  # Co

    @staticmethod
    def _generate_user_rows(users):

        for index, similar_user in enumerate(reversed(users)):
            username = similar_user.username
            status = core.users.statuses.get(username, UserStatus.OFFLINE)
            country_code = core.users.countries.get(username, "")
            stats = core.users.watched.get(username)
            rating = similar_user.rating

            if stats is not None:
                speed = stats.upload_speed
                files = stats.files
                folders = stats.folders
            else:
                speed = 0
                files = 0
                folders = 0

            yield [
                status,
                username,  # _KEY_COLUMN = 1 ("User")
                files,
                folders,
                speed,
                country_code,
                rating,
                index
                #index + (1000 * rating)
            ]


class _SimilarUserItem(UsersList.UserItem):

    def __init__(self, data):

        self.folders = data[3]
        self.speed = data[4] or 0

        self.rating = data[6] or 0  # sort by int
        self.index = data[7]

        data[3] = f"{self.folders:8d}" if self.folders is not None else ""
        data[4] = f"{human_speed(self.speed):>12}" if self.speed > 0 else ""
        data[5] = data[5] or "  "  # for resizeColumnToContents()
        data[6] = f"{self.rating:4d} =" if self.rating > 0 else f"{self.index:6d} ~"
        #data[7] = f"{data[7]:6d}"
        #data[8] = f"{data[8]:6d}"

        super().__init__(data)

    def setData(self, column, value, emit=True):

        if column == 3:
            if value is None or value == self.folders:
                return
            self.folders = value
            value = f"{self.folders:8d}"

        elif column == 4:
            if value is None or value == self.speed:
                return
            self.speed = value
            value = f"{human_speed(self.speed):>12}" if self.speed > 0 else ""

        return super().setData(column, value)

    def sortData(self, column):

        if column == 3:
            return self.folders

        if column == 4:
            return self.speed

        if column == 6:
            # Sort users by rating (largest number of identical likes) or
            # preserve default sort order by index if rating is not known
            return (self.rating, self.index)

        return super().sortData(column)


class _SimilarUsersList(UsersList):

    _SORT_COLUMN = 6  # ("Rating")
    _SORT_ORDER = ttk.TTkK.DescendingOrder

    class UserItem(_SimilarUserItem):
        pass

    def __init__(self, **kwargs):
        super().__init__(
            header=[
                " ",           # 0 = status
                _("User"),     # 1 = _KEY_COLUMN = 1
                _("Files"),    # 2
                _("Folders"),  # 3
                _("Speed"),    # 4
                _("Country"),  # 5
                "Rating",      # 6 = _SORT_COLUMN
                #"Index",
                #"I+^R"
            ],
            **kwargs
        )

        for col, width in enumerate([3, 30, 8, 8, 12, 3, 8]):  # , 8, 8]):
            self.setColumnWidth(col, width)

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_user_item_activated(self, user_item, _col):
        core.userinfo.show_user(str(user_item.data(self._KEY_COLUMN)))
