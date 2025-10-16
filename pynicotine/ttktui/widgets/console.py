# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import time
import datetime

import TermTk as ttk

#from pynicotine.cli import CLI
#from pynicotine.cli import cli
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.ttktui.widgets.menus import PopupMenu


class _ConsoleView(ttk.TTkAbstractScrollView):

    __slots__ = ('_lines', '_follow', '_timestamp_format')

    def __init__(self, *, follow:bool=False, **kwargs) -> None:
        super().__init__(**kwargs)

        self._find_line = -1
        self._find_pattern = ""
        self._find_timestamp = datetime.datetime.now().replace(microsecond=0)  # .timestamp()

        self._lines = [(self._find_timestamp, 0, ttk.TTkString("--- BOF ---"))]  # (timestamp, message_line_number, message)
        self._follow = follow

        self._timestamp_format = "%x %X"

        self._max_width = 0

        #TTkLog.installMessageHandler(self.loggingCallback)

        self.viewChanged.connect(self._viewChangedHandler)

    @ttk.pyTTkSlot()
    def _viewChangedHandler(self):
        self.update()

    def viewFullAreaSize(self) -> tuple[int,int]:
        #w = max( m.termWidth() for m in self._messages)
        #h = len(self._messages)
        return self._max_width, len(self._lines)

    #def loggingCallback(self, mode, context, message):
    def append(self, message, level=None):

        # Create new timestamped integer (UTC)
        timestamp = datetime.datetime.now().replace(microsecond=0) if level is not None else None
        color = None if timestamp else ttk.TTkColor.fg(config.sections["ui"].get("chatcommand", "") or "#908E8B")

        message_lines = message.split("\n")

        self._lines.extend(
            (timestamp, n, ttk.TTkString(line, color)) for n, line in enumerate(message_lines)
        )

        if not self.isVisible():
            return

        if not self.scroll_bottom(snap=len(message_lines)):
            # Log is shorter than height
            #self.viewChanged.emit()
            self.update()

    def scroll_bottom(self, force=False, snap=1):

        offx, offy = self.getViewOffsets()
        _, h = self.size()

        if force or self._follow and offy >= len(self._lines) - h - snap:
            offy = len(self._lines) - h
            return self.viewMoveTo(offx, offy)

        return False

    def _scroll_find_line(self, y, text=None, timestamp=None):

        if self._lines[y][0] is None or self._lines[y][0].timestamp() < self._find_timestamp.timestamp():
            if y < len(self._lines) - 1:
                return False

        if self._find_pattern:
            if not self._lines[y][2].search(regexp=self._find_pattern, ignoreCase=True):
                return False

        self._find_line = y

        _offx, offy = self.getViewOffsets()
        _, h = self.size()

        if offy <= y < (offy + h):
            # Line already within the viewable area
            self.viewChanged.emit()
        else:
            self.viewMoveTo(0, y - (h // 2))

        return True

    def scroll_find_prev(self):

        for y in range(self._find_line - 1, -1, -1):
            if self._scroll_find_line(y, text=self._find_pattern):
                return y

        self._find_line = len(self._lines)
        return len(self._lines)

    def scroll_find_next(self):

        for y in range(self._find_line + 1, len(self._lines)):
            if self._scroll_find_line(y, text=self._find_pattern):
                return y

        self._find_line = -1
        return -1

    def scroll_find_timestamp(self):

        for y in range(self._find_line, len(self._lines)):
            if self._scroll_find_line(y, timestamp=self._find_timestamp):
                return y

        self._find_line = -1
        return -1

    def set_find_timestamp(self, dt):

        self._find_timestamp = dt
        self._find_line = 0

        self.scroll_find_next()
        #self.viewChanged.emit()

        return bool(datetime)

    def set_find_pattern(self, text):

        self._find_pattern = str(text)
        self._find_line = -1

        self.viewChanged.emit()

        return bool(text)

    def paintEvent(self, canvas):

        if not self.isVisible():
            return

        ox, oy = self.getViewOffsets()
        _, h = self.size()

        for y, (timestamp, n, string) in enumerate(self._lines[oy:oy + h]):
            if self._find_pattern:
                # Highlight all the matching strings that are currently in view
                for match in string.findall(regexp=self._find_pattern, ignoreCase=True):
                    string = string.setColor(ttk.TTkColor.BLUE + ttk.TTkColor.BG_GREEN, match=match)

                    if self._find_line == oy + y:
                        # Navigating find next/prev, highlight the entire line
                        string = string.completeColor(ttk.TTkColor.MAGENTA + ttk.TTkColor.BG_CYAN)

            if timestamp is not None:
                # Create timestamp string from saved UTC integer (use localtime)
                timestamp_string = ttk.TTkString(
                    timestamp.strftime(self._timestamp_format),  #, time.localtime(timestamp)),
                    ttk.TTkColor.fg("#222222" if n else "#888888")
                )

                if self._find_timestamp and self._find_line == oy + y:
                    # Navigating date/time selector, highlight the timestamp
                    timestamp_string = timestamp_string.completeColor(ttk.TTkColor.BG_CYAN)

                string = timestamp_string + " " + string

            # Increase range of horizontal scrollbar if needed
            self._max_width = max(self._max_width, string.termWidth())

            canvas.drawTTkString(pos=(-ox, y), text=string)


class _ConsoleArea(ttk.TTkAbstractScrollArea):

    __slots__ = ('_console_view')

    def __init__(self, *, parent:ttk.TTkWidget=None, follow:bool=False, **kwargs) -> None:
        super().__init__(parent=parent, **kwargs)

        self._console_view = _ConsoleView(follow=follow)

        self.setHorizontalScrollBarPolicy(ttk.TTkK.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFocusPolicy(ttk.TTkK.ClickFocus)
        self.setViewport(self._console_view)

        self.popup_menu = None

    def mousePressEvent(self, evt):

        if evt.evt == ttk.TTkK.Press:
            if self.popup_menu is not None:
                self.popup_menu.close()
                self.popup_menu = None

            if evt.key == ttk.TTkK.RightButton:
                self.create_popup_menu()
                self.popup_menu.popup(evt.x, evt.y)
                return True

        return False

    def create_popup_menu(self):

        self.popup_menu = PopupMenu(self)  # , title=recommendation)
        self.popup_menu.addMenu(
            _("_Find…"), name="search_bar_toggle", checkable=True,
            checked=self.parentWidget().search_bar.isVisible()
        )
        #self.popup_menu.addSpacer()
        self.popup_menu.addMenu(
            "_Show command line", name="command_bar_toggle", checkable=True,
            checked=self.parentWidget().command_bar.isVisible()
        )
        self.popup_menu.addSpacer()
        self.popup_menu.addMenu(
            _("Clear Log View"), name="clear_log_view"
        )
        self.popup_menu.search_bar_toggle.toggled.connect(self.on_search_bar_toggled)
        self.popup_menu.command_bar_toggle.toggled.connect(self.on_command_bar_toggled)
        self.popup_menu.clear_log_view.menuButtonClicked.connect(self.on_clear_log_view)

    @ttk.pyTTkSlot(bool)
    def on_search_bar_toggled(self, is_visible):

        self.parentWidget().search_bar.setVisible(is_visible)
        self.parentWidget().search_bar.find_line.setEnabled(is_visible)

        if is_visible:
            self._console_view.scroll_bottom(snap=2)
            self.parentWidget().search_bar.find_line.setFocus()
            #self.parentWidget().command_line.clearFocus()
        else:
            self.parentWidget().search_bar.find_line.setCurrentText("")

    @ttk.pyTTkSlot(bool)
    def on_command_bar_toggled(self, is_visible):

        self.parentWidget().command_bar.setVisible(is_visible)
        self.parentWidget().command_line.setEnabled(is_visible)

        if is_visible:
            self._console_view.scroll_bottom(force=True)
            self.parentWidget().command_line.setFocus()
            #self.parentWidget().search_bar.find_line.clearFocus()

    @ttk.pyTTkSlot(ttk.TTkMenuButton)
    def on_clear_log_view(self, button):
        self._console_view._lines.clear()
        self._console_view.append("--- log cleared ---", level=1)
        self.parentWidget().search_bar.on_find_start()


class SearchBar(ttk.TTkFrame):

    def __init__(self, hint=_("Search log…"), **kwargs):
        super().__init__(layout=ttk.TTkHBoxLayout(), border=False, visible=False, **kwargs)

        self.find_time = ttk.TTkDateTime(parent=self, minWidth=20, maxWidth=20)

        self.find_time_start = ttk.TTkButton(parent=self, text= "↩", minWidth=3, maxWidth=3)  # ↩ ↪ ↚ ↛ ⍓ ⍌  ⃗  ⃖⃗ ⏁
        self.find_time_goto = ttk.TTkButton(parent=self, text= "▻◅", minWidth=4, maxWidth=4)  # ↩ ↪ ↚ ↛ ⍓ ⍌  ⃗  ⃖⃗ ⍑ ⏀
        self.find_time_end = ttk.TTkButton(parent=self, text= "↪", minWidth=3, maxWidth=3)  # ↩ ↪ ↚ ↛ ⍓ ⍌  ⃗  ⃖⃗ ⏂
        self.find_time_start.clicked.connect(self.on_find_start)
        self.find_time_goto.clicked.connect(self.on_find_goto)
        self.find_time_end.clicked.connect(self.on_find_end)

        self.layout().addWidget(ttk.TTkSpacer(maxWidth=10))

        self.find_prev = ttk.TTkButton(parent=self, text="⟑", minWidth=3, maxWidth=5)  # A
        self.find_prev.setToolTip(_("Find Previous Match"))

        self.find_next = ttk.TTkButton(parent=self, text="⟇", minWidth=3, maxWidth=5)  # ∀
        self.find_next.setToolTip(_("Find Next Match"))

        self.find_line = ttk.TTkComboBox(parent=self, editable=True, insertPolicy=ttk.TTkK.InsertPolicy.InsertAtTop)
        self.find_line.lineEdit()._hint = ttk.TTkString(hint)

        self.find_clear = ttk.TTkButton(parent=self, text="⌫", minWidth=3, maxWidth=3)
        self.find_clear.setToolTip("Clear Search Pattern")
        self.find_clear.clicked.connect(self.on_find_clear)

        self.layout().addWidget(ttk.TTkSpacer(maxWidth=10))
        self.layout().addWidget(ttk.TTkSpacer(maxWidth=30))

        #self.find_menu_bar = ttk.TTkMenuBarLayout()  # _("_Log Categories")
        #self.setMenuBar(self.find_menu_bar, position=ttk.TTkK.BOTTOM)

    @ttk.pyTTkSlot()
    def on_find_clear(self):

        if self.find_line.currentIndex() > -1:
            self.find_line._list.pop(self.find_line.currentIndex())
            self.find_line._id = -1

        self.find_line.setCurrentText("")
        self.find_line.setFocus()
        self.parentWidget()._console_area._console_view.set_find_pattern("")

        dt = self.parentWidget()._console_area._console_view._lines[0][0]  # earliest
        self.find_time.setDatetime(dt)
        self.on_find_end()

    @ttk.pyTTkSlot()
    def on_find_start(self):
        dt = self.parentWidget()._console_area._console_view._lines[0][0]  # earliest
        self.parentWidget()._console_area._console_view._find_line = -1
        self.find_time.setDatetime(dt)

    @ttk.pyTTkSlot()
    def on_find_goto(self):
        self.parentWidget()._console_area._console_view.set_find_timestamp(self.find_time.datetime())

    @ttk.pyTTkSlot()
    def on_find_end(self):
        dt = datetime.datetime.now().replace(microsecond=0)
        self.parentWidget()._console_area._console_view._find_line = -1
        self.find_time.setDatetime(dt)


class Console(ttk.TTkFrame):

    def __init__(self, **kwargs):
        super().__init__(layout=ttk.TTkVBoxLayout(), border=True, **kwargs)

        self.search_bar = SearchBar(parent=self)
        self._console_area = _ConsoleArea(parent=self, follow=True)
        self.command_bar = ttk.TTkFrame(parent=self, layout=ttk.TTkHBoxLayout(), border=False, visible=False)

        command_hint = _("Enter command…")

        self.command_prompt_box = ttk.TTkContainer(parent=self.command_bar, layout=ttk.TTkHBoxLayout(), visible=False)
        self.command_prompt = ttk.TTkLabel(
            parent=self.command_prompt_box, text="Custom prompt: ",
            color=ttk.TTkColor.YELLOW + ttk.TTkColor.BOLD, visible=True,
        )
        self.command_prompt.sizeChanged.connect(self.command_prompt_box.setMaximumSize)
        self.command_prompt.setText("")

        self.command_exec = ttk.TTkButton(
            parent=self.command_bar, text=ttk.TTkString(" ⃫", ttk.TTkColor.YELLOW + ttk.TTkColor.BOLD), data=None,
            minWidth=5, maxWidth=5  # > + / ╱ ↛ ⚂ ⏥ ⟈ ✐ ⟈ ⎆ ↵ ↱  ⃫
        )
        self.command_exec.setFocusPolicy(ttk.TTkK.FocusPolicy.ClickFocus)
        self.command_exec.setToolTip(command_hint)

        self.command_line = ttk.TTkLineEdit(
            parent=self.command_bar, hint=command_hint  # ttk.TTkString("Enter response…", ttk.TTkColor.BLINKING)
        )
        self.command_help = ttk.TTkButton(parent=self.command_bar, text="?", minWidth=3, maxWidth=3)  # ⍰
        self.command_help.setToolTip("CLI Command Help")

        self.scroll_toggle = ttk.TTkButton(
            parent=self.command_bar, text="∞", checkable=True, checked=False, minWidth=3, maxWidth=3  # ⇔ ↨ ↧ ⚙ ⟃⟄
        )
        self.scroll_toggle.toggled.connect(self.on_scroll_toggled)

        self.command_exec.clicked.connect(self.on_exec_clicked)
        self.command_line.returnPressed.connect(self.on_exec_pressed)
        self.command_help.clicked.connect(self.on_command_help)

        self.search_bar.find_time.datetimeChanged.connect(self._console_area._console_view.set_find_timestamp)

        self.search_bar.find_prev.clicked.connect(self._console_area._console_view.scroll_find_prev)
        self.search_bar.find_next.clicked.connect(self._console_area._console_view.scroll_find_next)
        self.search_bar.find_line.lineEdit().textChanged.connect(self._console_area._console_view.set_find_pattern)
        self.search_bar.find_line.currentTextChanged.connect(self._console_area._console_view.scroll_find_next)

        self.console_menu_bar = ttk.TTkMenuBarLayout()  # _("_Log Categories")
        self.command_menu_bar = ttk.TTkMenuBarLayout()  # ⌧ ⇔ ≏ ≎ ↧ ↥ ⇣ ∴ ∵ ▄ ◹ ⍡ ⏍

        self.enlarge_button = self.console_menu_bar.addMenu("⏏", data=12, alignment=ttk.TTkK.RIGHT_ALIGN)
        self.hide_button = self.command_menu_bar.addMenu(" ∵ ", data="", alignment=ttk.TTkK.CENTER_ALIGN)

        self.setMenuBar(self.console_menu_bar, position=ttk.TTkK.TOP)
        self.setMenuBar(self.command_menu_bar, position=ttk.TTkK.BOTTOM)

        self.closed.connect(self.destroy)

    def destroy(self):

        self._console_area._console_view.viewChanged.disconnect(self._console_area._console_view._viewChangedHandler)
        self.scroll_toggle.toggled.disconnect(self.on_scroll_toggled)
        self.command_prompt.sizeChanged.disconnect(self.command_prompt_box.setMaximumSize)
        self.command_line.returnPressed.disconnect(self.on_exec_pressed)
        self.command_help.clicked.disconnect(self.on_command_help)
        self.command_bar.close()

        self.search_bar.find_time.datetimeChanged.disconnect(self._console_area._console_view.set_find_timestamp)
        self.search_bar.find_prev.clicked.disconnect(self._console_area._console_view.scroll_find_prev)
        self.search_bar.find_next.clicked.disconnect(self._console_area._console_view.scroll_find_next)
        self.search_bar.find_line.lineEdit().textChanged.disconnect(self._console_area._console_view.set_find_pattern)
        self.search_bar.find_line.currentTextChanged.disconnect(self._console_area._console_view.scroll_find_next)
        self.search_bar.find_time.close()
        self.search_bar.close()

        self._console_area._console_view._lines.clear()
        self._console_area._console_view.close()
        self._console_area.close()

    def setVisible(self, is_visible):
        self._console_area.setVisible(is_visible)
        self._console_area._console_view.setVisible(is_visible)
        super().setVisible(is_visible)

    @ttk.pyTTkSlot()
    def on_command_help(self):
        events.emit_main_thread("cli-command", "help", "")
        self.command_line.setFocus()

    @ttk.pyTTkSlot(bool)
    def on_scroll_toggled(self, is_locked):
        self._console_area.setHorizontalScrollBarPolicy(
            ttk.TTkK.ScrollBarPolicy.ScrollBarAsNeeded if is_locked else ttk.TTkK.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self._console_area.on_search_bar_toggled(is_locked)

    @ttk.pyTTkSlot()  # Enter
    def on_exec_pressed(self):
        self._handle_prompt()

    @ttk.pyTTkSlot()  # Mouse
    def on_exec_clicked(self):
        self.command_line.setFocus()
        self._handle_prompt()

    def _handle_prompt(self):

        user_input = str(self.command_line.text()).strip()
        command_prompt = str(self.command_prompt.text())

        if not user_input and not command_prompt:
            self._console_area._console_view.scroll_bottom(force=True)
            return

        # Clear command line entry
        self.command_line.setText("")
        self.command_line.setEchoMode(self.command_line.EchoMode.Normal)
        self.command_prompt.setText("")
        self.command_prompt_box.setVisible(False)

        # Echo
        is_silent = (self.command_line.echoMode() != self.command_line.EchoMode.Normal)
        self.add_line(f'{command_prompt}{user_input if not is_silent else "*" * len(user_input)}')

        ## Check if custom prompt is active
        #if self._handle_prompt_callback(user_input, self.command_exec.data()):
        #    return

        # No custom prompt, treat input as command
        self._handle_prompt_command(user_input)

    def _handle_prompt_command(self, user_input):

        if not user_input:
            return False

        command, _separator, args = user_input.strip().partition(" ")
        args = args.strip()

        if command.startswith("/"):
            command = command[1:]

        events.emit_main_thread("cli-command", command, args)
        return True

    def add_line(self, message, level=None):
        self._console_area._console_view.append(message, level=level)
