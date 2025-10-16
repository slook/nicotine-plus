# SPDX-FileCopyrightText: 2020-2025 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2008-2011 quinox <quinox@users.sf.net>
# SPDX-FileCopyrightText: 2007 gallows <g4ll0ws@gmail.com>
# SPDX-FileCopyrightText: 2006-2009 daelstorm <daelstorm@gmail.com>
# SPDX-FileCopyrightText: 2003-2004 Hyriand <hyriand@thegraveyard.org>
# SPDX-License-Identifier: GPL-3.0-or-later

import re
import time

import TermTk as ttk

from pynicotine.config import config
from pynicotine.core import core
from pynicotine.logfacility import log
from pynicotine.ttktui.widgets.theme import URL_COLOR
from pynicotine.ttktui.widgets.theme import URL_COLOR_HEX
from pynicotine.ttktui.widgets.theme import USER_STATUS_COLORS
from pynicotine.ttktui.widgets.theme import USERNAME_STYLE
from pynicotine.slskmessages import UserStatus
from pynicotine.utils import find_whole_word


URL_REGEX = re.compile("(\\w+\\://[^\\s]+)|(www\\.\\w+\\.[^\\s]+)|(mailto\\:[^\\s]+)")


class Chatter(ttk.TTkSplitter):

    def __init__(self, chats, entity, send_message_callback, command_callback):
        super().__init__(border=False, orientation=ttk.TTkK.Direction.HORIZONTAL, name=entity)

        # self.user = user
        # self.room = room
        self.chats = chats
        # self.screen = chats.screen

        self.send_message_callback = send_message_callback
        self.command_callback = command_callback

        self.parse_urls = True

        self.type_tags = {
            "remote": ttk.TTkColor.fg(config.sections["ui"].get("chatremote", "").upper() or "#FFFFFF"),
            "local": ttk.TTkColor.fg(config.sections["ui"].get("chatlocal", "").upper() or "#9A9996"),
            "command": ttk.TTkColor.fg(config.sections["ui"].get("chatcommand", "").upper() or "#908E8B"),
            "action": ttk.TTkColor.fg(config.sections["ui"].get("chatme", "").upper() or "#908E8B"),
            "hilite": ttk.TTkColor.fg(config.sections["ui"].get("chathilite", "").upper() or "#5288CE")
        }

        # self.ticker_tape = ttk.TTkFrame(layout=ttk.TTkHBoxLayout(), maxHeight=1, border=False)
        self.finder = Finder(self)
        self.activity_view = None
        self.chat_view = ttk.TTkTextEdit(readOnly=True)

        self.chat_bar = ttk.TTkContainer(layout=ttk.TTkHBoxLayout())
        self.chat_send = ttk.TTkButton(
            parent=self.chat_bar, text=ttk.TTkString(">", ttk.TTkColor.BOLD), minWidth=5, maxWidth=5, enabled=False,
            addStyle={
                'default': {
                    'color': ttk.TTkColor.BOLD+ttk.TTkColor.WHITE + USER_STATUS_COLORS[UserStatus.ONLINE].invertFgBg(),
                },
            }
        )
        chat_hint = _("Send message…")
        self.chat_send.setToolTip(chat_hint)
        self.chat_send.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)

        self.chat_line = ttk.TTkLineEdit(parent=self.chat_bar, hint=chat_hint, enabled=False)

        # TTkEmojiButton
        def _emoji_picked(e):
            self.chat_emoj.setText(e)
            self.chat_line.setText(self.chat_line.text() + self.chat_emoj.text())
            self.chat_line.setFocus()

        @ttk.pyTTkSlot()
        def _show_emoji_picker():
            emoji_picker = ttk.TTkEmojiPicker(size=(40, 20))
            emoji_picker.emojiPicked.connect(_emoji_picked)
            ttk.TTkHelper.overlay(self.chat_emoj, emoji_picker, 0, 0)

        self.chat_emoj = ttk.TTkButton(parent=self.chat_bar, text='☻', minWidth=3, maxWidth=3, enabled=False)  # 😎 4
        self.chat_emoj.setToolTip("Insert Emoji")

        self.chat_help = ttk.TTkButton(parent=self.chat_bar, text="?", minWidth=3, maxWidth=3)
        self.chat_help.setToolTip(
            _("Private Chat Command Help") if chats.name == "private" else _("Chat Room Command Help")
        )

        self.log_toggle = ttk.TTkCheckbox(
            parent=self.chat_bar,
            maxWidth=6,
            text="Log",
            checked=(
                self.name() in config.sections["logging"]["private_chats" if chats.name() == "private" else "rooms"])
        )
        # self.log_toggle.setFocusPolicy(ttk.TTkK.FocusPolicy.TabFocus)
        self.log_toggle.setToolTip("Store Chat Messages in Log File")

        _spacer_right = ttk.TTkSpacer(parent=self.chat_bar, minWidth=1, maxWidth=1)

        self.chat_find = ttk.TTkButton(
            parent=self.chat_bar, text="⌕", checkable=True, checked=False, minWidth=3, maxWidth=3
        )
        self.chat_find.setToolTip("Search chat log…")

        self.user_list_button = None

        self.chat_send.clicked.connect(self.on_send_clicked)
        self.chat_line.returnPressed.connect(self.on_send_pressed)
        self.chat_emoj.clicked.connect(_show_emoji_picker)
        self.chat_help.clicked.connect(self.on_chat_help)
        self.chat_find.toggled.connect(self.finder.setVisible)
        self.log_toggle.toggled.connect(self.on_log_toggled)

        self.chat_container = ttk.TTkContainer(layout=ttk.TTkVBoxLayout())  # , paddingRight=-1
        self.chat_container.setPadding(0, 0, 1, 0)

        self.users_container = None
        self.users_spacer = None

        if chats.name() == "chatrooms" and entity != core.chatrooms.GLOBAL_ROOM_NAME:  # not chats.is_global
            self.chat_paned = ttk.TTkSplitter(orientation=ttk.TTkK.Direction.VERTICAL, paddingLeft=0)
            self.users_container = ttk.TTkContainer(layout=ttk.TTkVBoxLayout(), name="chatrooms", visible=False)
            self.users_header = ttk.TTkFrame(
                parent=self.users_container, layout=ttk.TTkHBoxLayout(), title="Users", name=entity,
                minHeight=3, maxHeight=3
            )
            self.users_spacer = ttk.TTkSpacer(parent=self.users_container)

            self.activity_view = ttk.TTkTextEdit(readOnly=True)
            self.activity_view.setFollowMode(ttk.TTkK.TextEditFollow.SMART)
            self.activity_view.sizeChanged.connect(self.on_activity_view_size_changed)

            self.activity_container = ttk.TTkContainer(layout=ttk.TTkVBoxLayout())  # , paddingRight=-1
            self.activity_container.layout().addWidget(self.activity_view)
            self.activity_container.setPadding(0, 0, 1, 0)

            self.chat_paned.insertWidget(0, self.activity_container, size=3)
            self.chat_paned.insertWidget(1, self.chat_container)

            self.insertWidget(0, self.chat_paned)
            # self.insertWidget(1, self.users_container, size=min(38, self.chats.screen.width() // 4))
        else:
            self.layout().addWidget(self.chat_container)

        # Open the log file now at this point in time for prepending old messages later
        self.log_lines = self.get_old_messages(
            num_lines=(
                config.sections["logging"]["readprivatelines" if self.chats.name() == "private" else "readroomlines"])
        )

        # Hide inner view widget (but keep outer scroll area) until finished loading
        self.chat_view.textEditView().setVisible(False)

    def load(self, is_enabled=False):

        self.toggle_chat_buttons()

        for widget in [self.chat_send, self.chat_emoj, self.chat_line]:
            widget.setEnabled(is_enabled)

        self.chats.screen.focus_default_widget()

        if self.chat_view.textEditView().isVisible():
            # Already loaded
            return

        # Yield to materialize page switch before loading
        timer = ttk.TTkTimer()
        timer.timeout.connect(self.load_chat_view)
        timer.start(0.25)

    def load_chat_view(self):

        if self.chats.currentWidget() != self:
            # transient switching
            return

        self.chat_container.layout().addWidget(self.finder)

        # self.chat_view = ttk.TTkTextEdit(readOnly=True)
        # self.chat_view.textEditView().setVisible(False)

        self.prepend_old_messages()

        self.chat_container.layout().addWidget(self.chat_view)
        self.chat_container.layout().addWidget(self.chat_bar)

        self.chat_view.setWordWrapMode(ttk.TTkK.WordWrap)
        self.chat_view.setLineWrapMode(ttk.TTkK.WidgetWidth, wrapEngine=ttk.TTkK.WrapEngine.FastWrap)  # HybridWrap

        self.chat_view.textEditView().setVisible(True)
        self.chat_view.scrollTo(ttk.TTkK.TextEditEdge.BOTTOM)
        self.chat_view.setFollowMode(ttk.TTkK.TextEditFollow.SMART)
        # self.chat_view.sizeChanged.connect(self.on_chat_view_size_changed)

        # self.chat_view.disableWidgetCursor(False)  # FIXME noop
        # self.chat_view.enableWidgetCursor(True)    # FIXME noop

        self.finder.setVisible(False)
        self.finder.find_load.setVisible(False)
        self.finder.find_line.lineEdit().setEnabled(True)

    def destroy(self):

        # for menu in self.popup_menus:
        #     menu.destroy()
        # self.chat_view.sizeChanged.disconnect(self.on_chat_view_size_changed)

        if self.users_container is not None:
            self.users_container.setVisible(False)

        # if self.chat_view is not None:
        self.chat_view.textEditView().setVisible(False)
        self.chat_view.clear()
        self.chat_view.setLineWrapMode(ttk.TTkK.NoWrap)
        self.chat_view.textEditView().viewMovedTo.clear()
        self.chat_view.textEditView().viewSizeChanged.clear()
        self.chat_view.textEditView().viewChanged.clear()
        self.chat_view.document().cursorPositionChanged.clear()
        self.chat_view.document().contentsChange.clear()
        self.chat_view.document().contentsChanged.clear()
        self.chat_view.document().formatChanged.clear()
        self.chat_view.document().undoAvailable.clear()
        self.chat_view.document().redoAvailable.clear()
        self.chat_view.currentColorChanged.clear()
        self.chat_view.cursorPositionChanged.clear()
        self.chat_view.undoAvailable.clear()
        self.chat_view.redoAvailable.clear()
        self.chat_view.textChanged.clear()
        self.chat_view.close()

        self.chat_line.returnPressed.disconnect(self.on_send_pressed)
        self.chat_line.close()

        self.chat_send.clicked.disconnect(self.on_send_clicked)
        self.chat_emoj.clicked.clear()
        self.chat_help.clicked.disconnect(self.on_chat_help)
        self.log_toggle.toggled.disconnect(self.on_log_toggled)
        self.log_lines.clear()

        if self.activity_view is not None:
            self.activity_view.sizeChanged.disconnect(self.on_activity_view_size_changed)
            self.activity_view.textEditView().setVisible(False)
            self.activity_view.clear()
            self.activity_view.setLineWrapMode(ttk.TTkK.NoWrap)
            self.activity_view.textEditView().viewMovedTo.clear()
            self.activity_view.textEditView().viewSizeChanged.clear()
            self.activity_view.textEditView().viewChanged.clear()
            self.activity_view.document().cursorPositionChanged.clear()
            self.activity_view.document().contentsChange.clear()
            self.activity_view.document().contentsChanged.clear()
            self.activity_view.document().formatChanged.clear()
            self.activity_view.document().undoAvailable.clear()
            self.activity_view.document().redoAvailable.clear()
            self.activity_view.currentColorChanged.clear()
            self.activity_view.cursorPositionChanged.clear()
            self.activity_view.undoAvailable.clear()
            self.activity_view.redoAvailable.clear()
            self.activity_view.textChanged.clear()
            self.activity_view.close()

        self.layout().clear()
        self.clean()
        # self.__dict__.clear()

    def _insert_line(self, line, prepend=False):

        self.chat_view.textCursor().insertText(
            ttk.TTkString("\n") + ttk.TTkString("").join(ttk.TTkString(text, color) for (text, color) in line),
            moveCursor=not prepend
        )

    def add_line(self, message, prepend=False, timestamp_format=None, message_type=None,
                 timestamp=None, timestamp_string=None, roomname=None, username=None):
        """Append or prepend a new chat message line with name tags and colors."""

        line = list(self._generate_chat_line(
            message,
            message_type=message_type,
            timestamp_string=timestamp_string,
            timestamp=timestamp,
            timestamp_format=timestamp_format,
            roomname=roomname,
            username=username
        ))
        self._insert_line(line, prepend=prepend)

    def _generate_chat_line(self, message, timestamp_format=None, message_type=None,
                            timestamp=None, timestamp_string=None, roomname=None, username=None):
        """Make a list of tuples [(text, tag),] for each element in line."""

        tag = self.type_tags.get(message_type)

        if timestamp_format:
            # Create timestamped string (use current localtime if timestamp is None)
            yield (time.strftime(timestamp_format, time.localtime(timestamp)), tag)
            yield (" ", tag)

        elif timestamp_string:
            # Use original timestamp string from log file (plus roomname for global feed)
            yield (timestamp_string, tag)
            yield (" ", tag)

        # Tag roomname, only used in global room feed
        if roomname:
            yield (roomname, self.get_room_tag(roomname))
            yield (" | ", tag)

        # Tag username with popup menu and away/online/offline colors
        if username:
            opener, closer = ("* ", " ") if message_type == "action" else ("[", "] ")

            yield (opener, tag)
            yield (username, self.get_user_tag(username))
            yield (closer, tag)

        # Highlight urls, if found and tag them
        yield from self._generate_hypertext(message, tag=tag)

    def _generate_hypertext(self, text, tag=None):

        if self.parse_urls and ("://" in text or "www." in text or "mailto:" in text):
            # Match first url
            match = URL_REGEX.search(text)

            while match:
                yield (text[:match.start()], tag)

                url = match.group()
                yield (url, ttk.TTkColor.fg(URL_COLOR_HEX, link=url))
                # Match remaining url
                text = text[match.end():]
                match = URL_REGEX.search(text)

        yield (text, tag)

    def get_room_tag(self, _roomname):
        return ttk.TTkColor.BOLD + URL_COLOR  # , modifier=ttk.TTkK.ColorType.Link))

    def get_user_tag(self, username):
        return USERNAME_STYLE + USER_STATUS_COLORS.get(core.users.statuses.get(username, UserStatus.OFFLINE))

    def get_old_messages(self, num_lines=0):
        """Gather list of raw log lines from file"""

        return log.read_log(
            folder_path=(log.private_chat_folder_path if self.chats.name() == "private" else log.room_folder_path),
            basename=self.name(),  # user | room
            num_lines=num_lines
        ) or []

    def prepend_old_messages(self):
        """Insert batch of previously gathered log lines from file"""

        self.chat_view.textCursor().movePosition(self.chat_view.textCursor().Start)

        if self.log_lines:  # and not self.loaded:  # chat_view.document().changed():
            self.add_line(_("--- old messages above ---"), message_type="hilite", prepend=True)

        for decoded_line in self.decode_log_lines(reversed(self.log_lines),
                                                  login_username=config.sections["server"]["login"]):

            timestamp_string, username, message, message_type = decoded_line

            self.add_line(
                message, prepend=True, message_type=message_type, timestamp_string=timestamp_string, username=username)

            if not self.finder.isVisible():
                self.add_line("--- loading stopped ---", message_type="hilite", prepend=True)
                break

        time.sleep(0.1)  # avoid oldest line appearing last
        self.chat_view.textCursor().movePosition(self.chat_view.textCursor().End)
        self.log_lines.clear()

    @staticmethod
    def decode_log_lines(log_lines, login_username=None):
        """Split encoded text bytestream into individual elements
        as required when reading raw chat log lines from disk."""

        login_username_lower = login_username.lower() if login_username else None

        for log_line in log_lines:
            try:
                line = log_line.decode("utf-8")

            except UnicodeDecodeError:
                line = log_line.decode("latin-1")

            timestamp_string = username = message = message_type = None

            if " [" in line and "] " in line:
                start = line.find(" [") + 2
                end = line.find("] ", start)

                if end > start:
                    timestamp_string = line[:start - 2]
                    username = line[start:end]
                    message = line[end + 2:]

                    if username == login_username:
                        message_type = "local"

                    elif login_username_lower and find_whole_word(login_username_lower, message.lower()) > -1:
                        message_type = "hilite"

                    else:
                        message_type = "remote"

            elif " * " in line:
                start = line.find(" * ")

                timestamp_string = line[:start]
                username = None  # indeterminate
                message = line[start + 1:]
                message_type = "action"

            yield timestamp_string, username, message or line, message_type

    def echo_message(self, message, message_type):

        if message_type == "command":
            timestamp_format = None
        elif self.chats.name() == "private":
            timestamp_format = config.sections["logging"]["private_timestamp"]
        else:
            timestamp_format = config.sections["logging"]["rooms_timestamp"]

        self.add_line(message, message_type=message_type, timestamp_format=timestamp_format)

    def toggle_chat_buttons(self):
        self.log_toggle.setVisible(
            not config.sections["logging"]["privatechat" if self.chats.name() == "private" else "chatrooms"])

    @ttk.pyTTkSlot(bool)
    def on_log_toggled(self, is_checked):

        config_key = "private_chats" if self.chats.name() == "private" else "rooms"

        if not is_checked:
            if self.name() in config.sections["logging"][config_key]:
                config.sections["logging"][config_key].remove(self.name())
            return

        if self.name() not in config.sections["logging"][config_key]:
            config.sections["logging"][config_key].append(self.name())

    @ttk.pyTTkSlot()
    def on_chat_help(self):
        self.command_callback(self.name(), "help", "")

    @ttk.pyTTkSlot(int, int)
    def on_chat_view_size_changed(self, w, h):
        if self.chat_view.textEditView()._smartFollowing:
            self.chat_view.scrollTo(ttk.TTkK.TextEditEdge.BOTTOM)

    @ttk.pyTTkSlot(int, int)
    def on_activity_view_size_changed(self, w, h):
        if self.activity_view.textEditView()._smartFollowing:
            self.activity_view.scrollTo(ttk.TTkK.TextEditEdge.BOTTOM)

    @ttk.pyTTkSlot()  # Enter
    def on_send_pressed(self):
        self.on_send_message()

    @ttk.pyTTkSlot()  # Mouse
    def on_send_clicked(self):
        self.chat_line.setFocus()
        self.on_send_message()

    def on_send_message(self):

        text = str(self.chat_line.text()).strip()

        if not text:
            self.chat_view.scrollTo(ttk.TTkK.TextEditEdge.BOTTOM)
            return

        is_double_slash_cmd = text.startswith("//")
        is_single_slash_cmd = (text.startswith("/") and not is_double_slash_cmd)

        if not is_single_slash_cmd:
            # Regular chat message

            self.chat_line.setText("")

            if is_double_slash_cmd:
                # Remove first slash and send the rest of the command as plain text
                text = text[1:]

            self.send_message_callback(self.name(), text)
            return

        cmd, _separator, args = text.partition(" ")
        args = args.strip()

        if not self.command_callback(self.name(), cmd[1:], args):
            return

        # Clear chat entry
        self.chat_line.setText("")


class Finder(ttk.TTkFrame):

    def __init__(self, chatter, hint=_("Search chat log…") + "NOT IMPLEMENTED", **kwargs):
        super().__init__(layout=ttk.TTkHBoxLayout(), border=False, visible=True, **kwargs)

        self.chatter = chatter

        # self.find_time = ttk.TTkDateTime(parent=self, minWidth=18, maxWidth=20)

        # self.find_back = ttk.TTkButton(parent=self, text="◄◅", minWidth=4, maxWidth=4)  # ↩ ↪ ↚ ↛ ⍓ ⍌  ⃗  ⃖⃗ ⏁
        # self.find_goto = ttk.TTkButton(parent=self, text="▻◅", minWidth=4, maxWidth=4)  # ↩ ↪ ↚ ↛ ⍓ ⍌  ⃗  ⃖⃗ ⏀ ⍑
        # self.find_skip = ttk.TTkButton(parent=self, text="▻►", minWidth=4, maxWidth=4)  # ↩ ↪ ↚ ↛ ⍓ ⍌  ⃗  ⃖⃗ ⏂
        # self.find_back.clicked.connect(self.on_find_back)
        # self.find_goto.clicked.connect(self.on_find_goto)
        # self.find_skip.clicked.connect(self.on_find_skip)

        self.layout().addWidget(ttk.TTkSpacer(minWidth=0, maxWidth=18))

        self.find_prev = ttk.TTkButton(parent=self, text="∆", minWidth=3, maxWidth=5)  # A ⟑
        self.find_prev.setToolTip(_("Find Previous Match"))

        self.find_next = ttk.TTkButton(parent=self, text="∇", minWidth=3, maxWidth=5)  # ∀ ⟇
        self.find_next.setToolTip(_("Find Next Match"))

        self.find_line = ttk.TTkComboBox(parent=self, editable=True, insertPolicy=ttk.TTkK.InsertPolicy.InsertAtTop)
        self.find_line.setMinimumWidth(len(hint) + 6)
        self.find_line.lineEdit().setEnabled(False)
        self.find_line.lineEdit()._hint = ttk.TTkString(hint)

        self.find_clear = ttk.TTkButton(parent=self, text="⌫", minWidth=3, maxWidth=5)
        self.find_clear.setToolTip("Clear Search Pattern")
        # self.find_clear.clicked.connect(self.on_find_clear)

        self.layout().addWidget(ttk.TTkSpacer(minWidth=2, maxWidth=10))

        self.find_hide = ttk.TTkButton(parent=self, text="☓", minWidth=3, maxWidth=5)  # A ⟑
        self.find_hide.clicked.connect(self.on_find_hide)

        self.load_box = ttk.TTkContainer(parent=self, minWidth=10, maxWidth=10)
        self.find_load = ttk.TTkLabel(parent=self.load_box)
        self.find_load.setText(ttk.TTkString("Loading…") + ttk.TTkString("…", ttk.TTkColor.BLINKING))

        self.layout().addWidget(ttk.TTkSpacer(minWidth=0, maxWidth=8))

    def setVisible(self, is_visible):

        if is_visible:
            self.show()
            self.find_line.setFocus()
        else:
            self.hide()
            self.chatter.chats.screen.focus_default_widget()

    @ttk.pyTTkSlot()
    def on_find_hide(self):
        self.chatter.chat_find.setChecked(False)
