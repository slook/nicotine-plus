# SPDX-FileCopyrightText: 2020-2026 Nicotine+ Contributors
# SPDX-FileCopyrightText: 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# SPDX-FileCopyrightText: 2009-2011 quinox <quinox@users.sf.net>
# SPDX-License-Identifier: GPL-3.0-or-later

import os

import TermTk as ttk

from pynicotine import __application_name__
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
#from pynicotine.gtkgui.application import GTK_API_VERSION
#from pynicotine.gtkgui.widgets import ui
#from pynicotine.gtkgui.widgets.filechooser import FileChooserButton
#from pynicotine.gtkgui.widgets.filechooser import FolderChooser
from pynicotine.ttktui.widgets.dialogs import Dialog
from pynicotine.ttktui.widgets.theme import NICOTINE_ICON
from pynicotine.ttktui.widgets.theme import NICOTINE_ICON_COLOR
#from pynicotine.gtkgui.widgets.dialogs import EntryDialog
#from pynicotine.gtkgui.widgets.popupmenu import PopupMenu
#from pynicotine.gtkgui.widgets.treeview import TreeView
from pynicotine.slskmessages import UserStatus


class FastConfigure(Dialog):

    def __init__(self, application):

        self.invalid_password = False
        self.invalid_username = False
        self.rescan_required = False
        self.finished = False

        # Setup Assistant Wizard Pager Navigation Buttons
        self.buttons_box = ttk.TTkContainer(layout=ttk.TTkHBoxLayout(), paddingLeft=1, paddingRight=1, maxHeight=3)
        self.previous_button = ttk.TTkButton(parent=self.buttons_box, text=_("_Previous"), border=True)
        self.previous_button.clicked.connect(self.on_previous)
        self.nav_spacer = ttk.TTkSpacer(parent=self.buttons_box)
        self.next_button = ttk.TTkButton(parent=self.buttons_box, text=_("_Next"), border=True)
        self.next_button.clicked.connect(self.on_next)

        # Setup Assistant Wizard Pager Window Content Container
        self.content_box = ttk.TTkContainer(layout=ttk.TTkVBoxLayout(), paddingLeft=1, paddingRight=1)

        super().__init__(
            parent=application.screen,
            content_box=self.content_box,
            buttons_box=self.buttons_box,
            #default_widget=self.next_button,
            show_callback=self.on_show,
            close_callback=self.on_close,
            title=_("Setup Assistant"),
            width=80,
            height=30,
            modal=True
            #show_title=False
        )

        #self.default_widget = self.next_button  # Focus shall be set after present() the overlay dialog window

        # Setup Assistant Wizard Pages
        self.welcome_page = ttk.TTkFrame(parent=self.content_box, title=_("Welcome to Nicotine+"), name="welcome_page")
        self.account_page = ttk.TTkFrame(parent=self.content_box, title="Soulseek Account", name="account_page")
        self.port_page = ttk.TTkFrame(parent=self.content_box, title="Network Port", name="port_page", visible=False)
        self.share_page = ttk.TTkContainer(parent=self.content_box, name="share_page", visible=False)
        self.summary_page = ttk.TTkFrame(parent=self.content_box, title="Setup Finished", name="summary_page")

        self.pages = [self.welcome_page, self.account_page, self.port_page, self.share_page, self.summary_page]

        for page in self.pages:
            page.setLayout(ttk.TTkVBoxLayout())

        events.connect("shares-ready", self._shares_ready)

    def load(self, parent):

        self.create_welcome_page(self.welcome_page)
        self.create_account_page(self.account_page)
        self.create_port_page(self.port_page)
        self.create_share_page(self.share_page)
        self.create_summary_page(self.summary_page)

        # TTkLabel widgets cannot word-wrap so instead we have to repurpose
        # TTkTextEdit in readOnly mode with text set after enabling wrapping
        self.texts = {
            "welcome_page": {
                self.welcome_intro_text: "Terminal client for the Soulseek peer-to-peer network"
            },
            "account_page": {
                self.account_intro_text: _(
                    "To create a new Soulseek account, fill in your desired username and password. If you already have "
                    "an account, fill in your existing login details."
                ),
                self.account_prompt_text: _(
                    "If your desired username is already taken, you will be prompted to change it."
                ),
                self.invalid_username_text: ttk.TTkString(
                    _("Username %s is invalid, please choose a different one. Usernames can only contain letters "
                      "(A-Z), numbers and spaces.") % config.sections["server"]["login"],
                    ttk.TTkColor.YELLOW
                ),
                self.invalid_password_text: ttk.TTkString(
                    _("User %s already exists, and the password you entered is invalid. Please choose a different "
                      "username if this is your first time logging in.") % config.sections["server"]["login"],
                    ttk.TTkColor.YELLOW
                )
            },
            "port_page": {
                self.port_intro_text: _(
                    "To connect with other Soulseek peers, a listening port on your router has to be forwarded to your "
                    "computer."
                ),
                self.port_users_text: _(
                    "If your listening port is closed, you will only be able to connect to users whose listening ports "
                    "are open."
                ),
                self.port_guide_text: _(
                    "If necessary, choose a different listening port below. This can also be done later in the "
                    "preferences."
                )
            },
            "share_page": {
                self.share_intro_text: _(
                    "Soulseek users will be able to download from your shares. Contribute to the Soulseek network by "
                    "sharing your own files and by resharing what you downloaded from other users."
                )
            },
            "summary_page": {
                self.summary_guide_text: _(
                    "Soulseek is an unencrypted protocol not intended for secure communication."
                ),
                self.summary_donate_text: _(
                    "Donating to Soulseek grants you privileges for a certain time period. If you have privileges, "
                    "your downloads will be queued ahead of non-privileged users."
                )
            }
        }

        for page in self.texts.values():
            for widget, text in page.items():
                #widget.setFocusPolicy(ttk.TTkK.FocusPolicy.NoFocus)
                widget.setLineWrapMode(ttk.TTkK.WidgetWidth)
                widget.setWordWrapMode(ttk.TTkK.WordWrap)
                widget.setText(text)

    def create_welcome_page(self, parent):

        if parent.layout().count():
            return

        welcome_labels_box = ttk.TTkContainer(
            parent=parent, layout=ttk.TTkVBoxLayout(), paddingTop=2, paddingLeft=2, paddingRight=2
        )
        welcome_labels_box.layout().addWidget(ttk.TTkSpacer())
        #self.main_icon = ttk.TTkImage(parent=welcome_labels_box, rasteriser=ttk.TTkImage.HALFBLOCK)
        #self.main_icon.setData(
        self.icon_label = ttk.TTkLabel(parent=welcome_labels_box, text=NICOTINE_ICON, alignment=ttk.TTkK.CENTER_ALIGN)
        self.icon_label.setMinimumHeight(str(NICOTINE_ICON).count("\n") + 1)
        self.welcome_intro_label = ttk.TTkLabel(
            parent=welcome_labels_box,
            text=ttk.TTkString(__application_name__, ttk.TTkColor.BOLD + NICOTINE_ICON_COLOR),
            alignment=ttk.TTkK.CENTER_ALIGN,
            maxHeight=1
        )
        welcome_labels_box.layout().addWidget(ttk.TTkSpacer())

        welcome_widgets_box = ttk.TTkContainer(
            parent=parent, layout=ttk.TTkHBoxLayout(), paddingBottom=1, paddingLeft=4, paddingRight=4
        )
        welcome_widgets_box.layout().addWidget(ttk.TTkSpacer())
        self.welcome_intro_text = ttk.TTkTextEdit(parent=welcome_widgets_box, readOnly=True, minWidth=54)
        welcome_widgets_box.layout().addWidget(ttk.TTkSpacer(maxHeight=4))

    def create_account_page(self, parent):

        if parent.layout().count():
            return

        account_guide_labels_box = ttk.TTkContainer(
            parent=parent, layout=ttk.TTkVBoxLayout(), paddingTop=2, paddingLeft=2, paddingRight=2
        )
        self.account_intro_text = ttk.TTkTextEdit(parent=account_guide_labels_box, readOnly=True)
        self.account_prompt_text = ttk.TTkTextEdit(parent=account_guide_labels_box, readOnly=True)
        self.invalid_username_text = ttk.TTkTextEdit(parent=account_guide_labels_box, readOnly=True, visible=False)
        self.invalid_password_text = ttk.TTkTextEdit(parent=account_guide_labels_box, readOnly=True, visible=False)

        account_widgets_box = ttk.TTkContainer(
            parent=parent, layout=ttk.TTkGridLayout(), paddingBottom=1, paddingLeft=4, paddingRight=4
        )
        self.username_entry = ttk.TTkLineEdit(maxWidth=core.users.USERNAME_MAX_LENGTH)
        self.username_entry.textEdited.connect(self.on_account_entry_edited)
        self.username_entry.returnPressed.connect(self.on_account_entry_activated)
        self.username_entry.validated = True  # don't show warning when username empty initially

        self.password_entry = ttk.TTkLineEdit(echoMode=ttk.TTkLineEdit.EchoMode.Password)
        self.password_entry.textEdited.connect(self.on_account_entry_edited)
        self.password_entry.returnPressed.connect(self.on_account_entry_activated)

        account_widgets_box.layout().addWidget(ttk.TTkLabel(text=_("Username:"), maxHeight=1), 0, 0)
        account_widgets_box.layout().addWidget(self.username_entry, 1, 0)
        account_widgets_box.layout().addWidget(ttk.TTkSpacer(maxWidth=4), 0, 1)
        account_widgets_box.layout().addWidget(ttk.TTkLabel(text=_("Password:"), maxHeight=1), 0, 2)
        account_widgets_box.layout().addWidget(self.password_entry, 1, 2)

        self.account_info_bar = ttk.TTkLabel(parent=parent, alignment=ttk.TTkK.CENTER_ALIGN, maxHeight=1)

    def create_port_page(self, parent):

        if parent.layout().count():
            return

        port_labels_box = ttk.TTkContainer(
            parent=parent, layout=ttk.TTkVBoxLayout(), paddingTop=1, paddingLeft=2, paddingRight=2
        )
        self.port_intro_text = ttk.TTkTextEdit(parent=port_labels_box, readOnly=True)
        self.port_users_text = ttk.TTkTextEdit(parent=port_labels_box, readOnly=True)
        self.port_guide_text = ttk.TTkTextEdit(parent=port_labels_box, readOnly=True)

        port_widgets_box = ttk.TTkContainer(parent=self.port_page, layout=ttk.TTkGridLayout(), paddingBottom=1)

        self.listen_port_entry = ttk.TTkSpinBox(value=2234, maximum=65535, minimum=1)
        self.listen_port_entry.valueChanged.connect(self.on_port_entry_edited)
        self.listen_port_entry._lineEdit.returnPressed.connect(self.on_port_entry_activated)

        self.default_port_button = ttk.TTkButton(text="↺", maxWidth=3, enabled=False)
        self.default_port_button.setToolTip("Reset to Default")
        self.default_port_button.clicked.connect(self.on_default_port)

        port_widgets_box.layout().addWidget(
            ttk.TTkLabel(text=_("Listening port (TCP):"), maxWidth=30, maxHeight=1), 0, 1
        )
        port_widgets_box.layout().addWidget(self.listen_port_entry, 1, 1)
        port_widgets_box.layout().addWidget(self.default_port_button, 1, 2)
        port_widgets_box.layout().addWidget(ttk.TTkSpacer(), 0, 0)
        port_widgets_box.layout().addWidget(ttk.TTkSpacer(), 0, 3)

        self.port_info_bar = ttk.TTkLabel(parent=parent, alignment=ttk.TTkK.CENTER_ALIGN, maxHeight=1)

    def create_share_page(self, parent):

        if parent.layout().count():
            return

        # Download Folder
        self.download_frame = ttk.TTkFrame(
            parent=parent, title=_("Download Files to Folder"), layout=ttk.TTkGridLayout(rowMinHeight=1)
        )
        self.download_frame.layout().addWidget(ttk.TTkSpacer(maxWidth=8), 1, 0)
        self.download_frame.layout().addWidget(ttk.TTkSpacer(maxWidth=8), 1, 3)

        self.refresh_download_folder_menu = ttk.TTkMenuBarLayout()
        self.refresh_download_folder_button = self.refresh_download_folder_menu.addMenu(" ↻ ")
        self.refresh_download_folder_button.setToolTip("Refresh")
        self.refresh_download_folder_button.menuButtonClicked.connect(self.reset_completeness)
        self.download_frame.setMenuBar(self.refresh_download_folder_menu)

        self.download_folder_button = ttk.TTkFileButtonPicker(
            caption=_("Select a Folder") + " for Storing Downloads",
            fileMode=ttk.TTkK.FileMode.Directory,
            filter=f"Folders (*{os.sep});;All Files (*)"
        )
        self.download_folder_button.folderPicked.connect(self.on_download_folder_selected)

        self.default_download_folder_button = ttk.TTkButton(text="↺", maxWidth=3)
        self.default_download_folder_button.setToolTip("Reset to Default")
        self.default_download_folder_button.clicked.connect(self.on_default_download_folder)

        self.download_info_bar = ttk.TTkLabel(alignment=ttk.TTkK.CENTER_ALIGN, maxHeight=1)

        self.download_frame.layout().addWidget(self.download_folder_button, 1, 1)
        self.download_frame.layout().addWidget(self.default_download_folder_button, 1, 2)
        self.download_frame.layout().addWidget(self.download_info_bar, 2, 0, 1, 4)

        # Share Folders
        shares_frame = ttk.TTkFrame(parent=parent, title=_("Share Folders"), layout=ttk.TTkVBoxLayout())
        share_widgets_box = ttk.TTkContainer(
            parent=shares_frame, layout=ttk.TTkVBoxLayout(),
            paddingTop=1, paddingBottom=0, paddingLeft=2, paddingRight=2
        )
        self.share_intro_text = ttk.TTkTextEdit(parent=share_widgets_box, readOnly=True, maxHeight=4)

        shares_list_container = ttk.TTkFrame(parent=share_widgets_box, layout=ttk.TTkVBoxLayout(), paddingBottom=-1)
        self.shares_list_view = ttk.TTkTree(
            parent=shares_list_container, header=[" ", _("Folder"), _("Virtual Folder")],
            selectionMode=ttk.TTkK.SelectionMode.MultiSelection, name="shares_list", minHeight=3
        )
        self.shares_list_view.setColumnWidth(0, 3)
        self.shares_list_view.setColumnWidth(1, 34)
        self.shares_list_view.setColumnWidth(2, 24)
        self.shares_list_view.itemClicked.connect(self.on_shared_folder_clicked)
        self.shares_list_view.itemActivated.connect(self.on_shared_folder_activated)

        shares_buttons_box = ttk.TTkContainer(
            parent=share_widgets_box, layout=ttk.TTkHBoxLayout(), paddingLeft=1, paddingRight=1, maxheight=1
        )
        self._add_shared_folder_button = ttk.TTkFileButtonPicker(
            parent=shares_buttons_box, text=_("Add…"), caption=_("Select a Folder") + " to Share",
            fileMode=ttk.TTkK.FileMode.Directory, filter=f"Folders (*{os.sep});;All Files (*)"
        )
        self._add_shared_folder_button.folderPicked.connect(self.on_add_shared_folder_selected)

        self._edit_shared_folder_button = ttk.TTkButton(parent=shares_buttons_box, text=_("Edit…"), enabled=False)
        self._edit_shared_folder_button.clicked.connect(self.on_edit_shared_folder)

        self._remove_shared_folder_button = ttk.TTkButton(parent=shares_buttons_box, text=_("Remove"), enabled=False)
        self._remove_shared_folder_button.clicked.connect(self.on_remove_shared_folder)

        shares_buttons_box.layout().addWidget(ttk.TTkSpacer())
        shares_buttons_box.layout().addWidget(ttk.TTkSpacer())

        self.shares_count_label = ttk.TTkLabel(
            parent=shares_buttons_box, text="Listing shares…", alignment=ttk.TTkK.RIGHT_ALIGN
        )
        self.shares_list_view._treeView.viewSizeChanged.connect(self.on_shares_list_changed)

        self.shares_info_bar = ttk.TTkLabel(parent=shares_frame, alignment=ttk.TTkK.CENTER_ALIGN, maxHeight=1)

    def create_summary_page(self, parent):

        if parent.layout().count():
            return

        summary_guide_labels_box = ttk.TTkContainer(
            parent=parent, layout=ttk.TTkVBoxLayout(), paddingTop=2, paddingLeft=2, paddingRight=2
        )
        summary_guide_labels_box.layout().addWidget(ttk.TTkSpacer())
        summary_done_icon = ttk.TTkString(" ✅ ", ttk.TTkColor.BOLD + ttk.TTkColor.GREEN)
        self.summary_intro_label = ttk.TTkLabel(
            parent=summary_guide_labels_box,
            text=summary_done_icon + ttk.TTkString(_("You are ready to use Nicotine+!"), ttk.TTkColor.BOLD),
            alignment=ttk.TTkK.CENTER_ALIGN,
            maxHeight=1
        )
        summary_guide_labels_box.layout().addWidget(ttk.TTkSpacer())
        self.summary_guide_text = ttk.TTkTextEdit(parent=summary_guide_labels_box, readOnly=True)
        self.summary_donate_text = ttk.TTkTextEdit(parent=summary_guide_labels_box, readOnly=True)
        summary_guide_labels_box.layout().addWidget(ttk.TTkSpacer())

    def reset_completeness(self):
        """Turns on the complete flag if everything required is filled in."""

        page = self.get_visible_page()
        page_complete = (
            (page in (self.welcome_page, self.summary_page))
            or (page == self.account_page and self._validate_username_entry() and self._validate_password_entry())
            or (page == self.port_page and self._validate_port_entry())
            or (page == self.share_page and self._validate_download_folder_path())
        )
        self.next_button.setEnabled(page_complete)

    def _validate_username_entry(self):

        if self.username_entry.validated:
            return True

        error = ""
        entry = str(self.username_entry.text())

        if not entry:
            error = "Username empty!"

        elif len(entry) > core.users.USERNAME_MAX_LENGTH:
            error = "Username too long. Max %i characters allowed!" % core.users.USERNAME_MAX_LENGTH

        elif entry != entry.strip():
            error = "No leading and trailing spaces allowed in username!"

        elif not entry.isascii():
            error = "Invalid characters in username!"

        self.account_info_bar.setText(error)
        self.account_info_bar.setColor(ttk.TTkColor.BOLD+ttk.TTkColor.BG_RED if error else ttk.TTkColor.RST)

        self.username_entry.validated = bool(entry and not error)
        return self.username_entry.validated

    def _validate_password_entry(self):
        error = ""
        entry = str(self.password_entry.text())
        if not entry and self.username_entry.validated and self.username_entry.text() and self.password_entry.hasFocus():
            error = "Password empty!"
        elif self.invalid_password and str(self.username_entry.text()) == config.sections["server"]["login"]:
            if entry == config.sections["server"]["passw"]:
                error = "Username taken or invalid password!"
        self.account_info_bar.setText(error)
        self.account_info_bar.setColor(ttk.TTkColor.BOLD+ttk.TTkColor.BG_RED if error else ttk.TTkColor.RST)
        return bool(entry and not error)

    def _validate_port_entry(self):
        error = ""
        if self.listen_port_entry.value() < 1024:
            error = "Listening port not permitted!"
        self.port_info_bar.setText(error)
        self.port_info_bar.setColor(ttk.TTkColor.BOLD+ttk.TTkColor.BG_RED if error else ttk.TTkColor.RST)
        return bool(not error)

    @ttk.pyTTkSlot()  # Return Key
    def on_account_entry_activated(self):

        self.username_entry.validated = False

        if not self._validate_username_entry():
            self.account_info_bar.setColor(self.account_info_bar.color()+ttk.TTkColor.BLINKING)
            self.username_entry.setFocus()
            return

        if not self._validate_password_entry():
            self.account_info_bar.setColor(self.account_info_bar.color()+ttk.TTkColor.BLINKING)
            self.password_entry.setFocus()
            return

        self.on_next()

    @ttk.pyTTkSlot(str)
    def on_account_entry_edited(self, _text):
        self.username_entry.validated = False
        self.reset_completeness()

    @ttk.pyTTkSlot()  # Return Key
    def on_port_entry_activated(self):

        if not self._validate_port_entry():
            self.port_info_bar.setColor(self.port_info_bar.color()+ttk.TTkColor.BLINKING)
            self.listen_port_entry.setFocus()
            return

        self.on_next()

    @ttk.pyTTkSlot(int)
    def on_port_entry_edited(self, value):

        self.default_port_button.setEnabled(value != config.defaults["server"]["portrange"][0])

        is_changed = (value != config.sections["server"]["portrange"][0])
        self.default_port_button.setToolTip("Undo" if is_changed else "Reset to Default")
        self.default_port_button.setText("↶" if is_changed else "↺")

        self.reset_completeness()

    @ttk.pyTTkSlot()
    def on_default_port(self, factory=True):

        if self.listen_port_entry.value() != config.sections["server"]["portrange"][0]:
            factory = False  # Undo

        port, _unused = config.defaults["server"]["portrange"] if factory else config.sections["server"]["portrange"]
        self.listen_port_entry.setValue(port)
        self.next_button.setFocus()

    def _validate_download_folder_path(self):

        error = ""
        try:
            self.default_download_folder_button.setEnabled(
                not os.path.samefile(
                    os.path.expandvars(config.sections["transfers"]["downloaddir"]),
                    os.path.expandvars(config.defaults["transfers"]["downloaddir"])
                )
            )
            self.refresh_download_folder_button.setVisible(False)

        except OSError as err:
            error = err
            self.refresh_download_folder_button.setVisible(True)
            self.refresh_download_folder_menu.update()  # workaround button invisible until hover

            if self.get_visible_page() == self.share_page:
                self.download_folder_button.setFocus()

        self.download_info_bar.setColor(ttk.TTkColor.BOLD+ttk.TTkColor.BG_RED if error else ttk.TTkColor.RST)
        self.download_info_bar.setToolTip(ttk.TTkString(error, self.download_info_bar.color()))
        self.download_info_bar.setText(_("Download folder error") if error else "")
        return bool(not error)

    @ttk.pyTTkSlot(str)
    def on_download_folder_selected(self, path):

        # More lenient solution than os.path.basename() to avoid empty strings
        self.download_folder_button.setText(path.rstrip(os.sep).rpartition(os.sep)[-1] or path)
        self.download_folder_button.setPath(os.path.expandvars(path.rstrip(os.sep)))
        self.download_folder_button.setToolTip(self.download_folder_button.path())  # Show path without env variables

        if self._validate_download_folder_path():
            config.sections["transfers"]["downloaddir"] = path.rstrip(os.sep)

    @ttk.pyTTkSlot()
    def on_default_download_folder(self, factory=True):
        self.on_download_folder_selected(
            config.defaults["transfers"]["downloaddir"] if factory else core.downloads.get_default_download_folder())

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_shared_folder_clicked(self, _share_item, _col):
        is_selections = bool(self.shares_list_view.selectedItems())
        self._edit_shared_folder_button.setEnabled(is_selections)
        self._remove_shared_folder_button.setEnabled(is_selections)

    @ttk.pyTTkSlot(ttk.TTkTreeWidgetItem, int)
    def on_shared_folder_activated(self, _share_item, _col):
        self.on_edit_shared_folder()

    @ttk.pyTTkSlot()
    def on_shares_list_changed(self):
        self.shares_count_label.setText("%i public shares" % self.shares_list_view.invisibleRootItem().size())

    def _add_share_item(self, virtual_name, folder_path, unreadable_shares=None):

        if unreadable_shares is None:
            unreadable_shares = core.shares.check_shares_available()

        if (virtual_name, folder_path) in unreadable_shares:
            icon = ttk.TTkString(" 🛇 ", ttk.TTkColor.BOLD + ttk.TTkColor.RED + ttk.TTkColor.BLINKING)
            icon_label = _("Unreadable")
        else:
            icon = ""
            icon_label = ""
            self._add_shared_folder_button.setPath(os.path.dirname(folder_path.rstrip(os.sep)))

        share_item = ttk.TTkTreeWidgetItem([icon_label, folder_path, virtual_name])
        share_item.setIcon(0, icon)

        self.shares_list_view.addTopLevelItem(share_item)
        return share_item

    @ttk.pyTTkSlot(str)
    def on_add_shared_folder_selected(self, folder_path):

        virtual_name = core.shares.add_share(folder_path)

        if not virtual_name:
            basename = folder_path.rstrip(os.sep).rpartition(os.sep)[-1] or folder_path
            self.shares_info_bar.setText(_("Cannot share inaccessible folder \"%s\"") % basename)
            self.shares_info_bar.setColor(ttk.TTkColor.BOLD+ttk.TTkColor.BG_RED)
            return

        self._add_share_item(virtual_name, folder_path)

        self.shares_info_bar.setText(
            _("Added %(group_name)s share \"%(virtual_name)s\" (rescan required)") % {
                "group_name": "public",
                "virtual_name": virtual_name
            }
        )
        self.shares_info_bar.setColor(ttk.TTkColor.GREEN)

        self.rescan_required = True
        self.next_button.setFocus()

    @ttk.pyTTkSlot()
    def on_edit_shared_folder(self):

        from pynicotine.ttktui.widgets.dialogs import EntryDialog

        def response(dialog, _response_id, old_share_item):

            new_virtual_name = dialog.get_entry_value()

            if new_virtual_name == old_virtual_name:
                return

            core.shares.remove_share(old_virtual_name)

            old_share_item.setHidden(True)  # workaround to remove item
            #self.shares_list_view.invisibleRootItem().removeChild(old_share_item)  # FIXME item not removed

            new_virtual_name = core.shares.add_share(folder_path, virtual_name=new_virtual_name, validate_path=False)
            new_share_item = self._add_share_item(new_virtual_name, folder_path)

            self.shares_info_bar.setText(
                ttk.TTkString(
                    _("Added %(group_name)s share \"%(virtual_name)s\" (rescan required)") % {
                        "group_name": "public",
                        "virtual_name": new_virtual_name
                    }, ttk.TTkColor.GREEN)
            )
            self.rescan_required = True

        for share_item in reversed(self.shares_list_view.selectedItems()):
            if share_item.isHidden():
                # Already removed workaround
                continue

            old_virtual_name = str(share_item.data(2))
            folder_path = str(share_item.data(1))

            EntryDialog(
                parent=self.window,
                title=_("Edit Shared Folder"),
                message=_("Enter new virtual name for '%(dir)s':") % {"dir": folder_path},
                default=old_virtual_name,
                action_button_label=_("_Edit"),
                callback=response,
                callback_data=share_item
            ).present()
            return

        self._edit_shared_folder_button.setEnabled(False)  # bool(self.shares_list_view.selectedItems()))

    @ttk.pyTTkSlot()
    def on_remove_shared_folder(self):

        for share_item in reversed(self.shares_list_view.selectedItems()):
            if share_item.isHidden():
                # Already removed workaround
                continue

            virtual_name = str(share_item.data(2))

            if core.shares.remove_share(virtual_name):
                self.shares_info_bar.setText(_("Removed share \"%s\" (rescan required)") % virtual_name)
                self.shares_info_bar.setColor(ttk.TTkColor.GREEN)
            else:
                self.shares_info_bar.setText(_("No share with name \"%s\"") % virtual_name)
                self.shares_info_bar.setColor(ttk.TTkColor.BOLD+ttk.TTkColor.BG_RED)

            #self.shares_list_view.invisibleRootItem().removeChild(share_item)  ## FIXME item not removed from tree
            share_item.setHidden(True)
            self.rescan_required = True

        self._remove_shared_folder_button.setEnabled(False)  # bool(self.shares_list_view.selectedItems()))

    def get_visible_page(self):
        for page in self.pages:
            if page.isVisible():
                return page

    def set_visible_page(self, new_page):
        for page in self.pages:
            page.setVisible(page == new_page)

        self.on_page_change(new_page)

    def set_visible_page_index(self, new_index):
        for page_index, page in enumerate(self.pages):
            page.setVisible(page.isEnabled() and page_index == new_index)

        return any(page.isVisible() for page in self.pages)

    def on_page_change(self, page):

        change_account = self.invalid_password or self.invalid_username
        self.finished = (page == self.account_page if change_account else page == self.summary_page)
        self.next_button.setText(_("_Finish") if self.finished else _("_Next"))
        self.previous_button.setText(_("_Cancel") if change_account else _("_Previous"))
        self.previous_button.setVisible(page != self.welcome_page)

        if page == self.welcome_page:
            self.window.setWindowFlag(ttk.TTkK.WindowFlag.WindowCloseButtonHint)
        elif page == self.share_page:
            self.window.setWindowFlag(ttk.TTkK.WindowFlag.WindowMaximizeButtonHint)
            #self.listen_port_entry._lineEdit.clearFocus()  # workaround edit cursor not hidden
        else:
            self.window.setWindowFlag(ttk.TTkK.WindowFlag.NONE)

        if page == self.account_page:
            self.password_entry.setFocus()     # workaround stuck focus style
            self.password_entry.clearFocus()   # workaround stuck focus style
            self.username_entry.setFocus()
        elif page == self.port_page:
            self.listen_port_entry.setFocus()  # workaround lineedit widget invisible
            self.next_button.setFocus()
        else:
            self.next_button.setFocus()

        self.reset_completeness()

    @ttk.pyTTkSlot()
    def on_next(self):

        next_index = self.pages.index(self.get_visible_page()) + 1

        if self.finished or next_index >= len(self.pages):
            self.on_finished(account_required=self.invalid_password or self.invalid_username or config.need_config())
            return

        while not self.set_visible_page_index(next_index) and next_index < len(self.pages):
            # Skip disabled page
            next_index += 1

        self.on_page_change(self.get_visible_page())

    @ttk.pyTTkSlot()
    def on_previous(self):

        previous_index = self.pages.index(self.get_visible_page()) - 1

        if self.invalid_password or previous_index < 0:
            self.close()
            return

        while not self.set_visible_page_index(previous_index) and previous_index >= 0:
            # Skip disabled page
            previous_index -= 1

        self.on_page_change(self.get_visible_page())

    def on_finished(self, account_required=False):

        # Close the setup assistant window to allow other dialogs to spawn
        self.close()

        # share_page
        if self.rescan_required:
            core.shares.rescan_shares()

        # port_page
        listen_port = self.listen_port_entry.value()
        config.sections["server"]["portrange"] = (listen_port, listen_port)

        # account_page
        if account_required:
            core.users.log_in_as(str(self.username_entry.text()), str(self.password_entry.text()))
            self.password_entry.setText("")

        elif core.users.login_status == UserStatus.OFFLINE:
            core.connect()

    def on_close(self, window):

        self.invalid_password = False
        self.invalid_username = False

        self.account_info_bar.setText("")
        self.shares_info_bar.setText("")
        self._edit_shared_folder_button.setEnabled(False)
        self._remove_shared_folder_button.setEnabled(False)

    def _shares_ready(self, successful):
        self.rescan_required = (not successful)

    def on_show(self, window):

        self.load(window.layout())

        change_account = self.invalid_password or self.invalid_username
        self.account_page.setEnabled(change_account or config.need_config())

        # account_page
        self.username_entry.setText(config.sections["server"]["login"])
        self.password_entry.setText(config.sections["server"]["passw"])

        self.invalid_username_text.setVisible(self.invalid_username)
        self.invalid_password_text.setVisible(self.invalid_password)
        self.account_prompt_text.setVisible(not change_account)

        # port_page
        self.on_default_port(factory=False)

        # share_page
        self.on_default_download_folder(factory=False)

        self.shares_list_view.clear()
        self.shares_list_view._treeView.setSortingEnabled(False)

        unreadable_shares = core.shares.check_shares_available()

        for virtual_name, folder_path, *_unused in config.sections["transfers"]["shared"]:
            self._add_share_item(virtual_name, folder_path, unreadable_shares=unreadable_shares)

        self.shares_list_view._treeView.setSortingEnabled(True)
        self.shares_list_view.sortItems(2, ttk.TTkK.AscendingOrder)  # Virtual Folder

        self.set_visible_page(self.account_page if change_account else self.welcome_page)
