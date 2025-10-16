# SPDX-FileCopyrightText: 2025-2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

from pynicotine.config import config
from pynicotine.slskmessages import UserStatus
from TermTk import TTkColor
from TermTk import TTkConstant
from TermTk import TTkString


NICOTINE_ICON_COLOR = TTkColor.fg('#FFAA40')  # TTkColor.fg('#D38C2D')  # TTkColor.bg('#FFAA40')
NICOTINE_ICON = TTkString(
    "                \n"
    " ███████▄       \n"
    " ███▀▀████      \n"
    " ███   ███      \n"
    " ███   ███  ██  \n"
    " ███   █████████\n"
    " ███   ███  ██  \n"
    "                ",
    NICOTINE_ICON_COLOR
)
TAB_COLORS = {
    "default": TTkColor.fg(config.sections["ui"].get("tab_default").upper() or "#FFFFFF"),
    "changed": TTkColor.fg(config.sections["ui"].get("tab_changed").upper() or "#497EC2") + TTkColor.BOLD,
    "hilite": TTkColor.fg(config.sections["ui"].get("tab_hilite").upper() or "#F5C211") + TTkColor.BOLD
}
URL_COLOR_HEX = config.sections["ui"].get("urlcolor", "").upper() or "#5288CE"
URL_COLOR = TTkColor.fg(URL_COLOR_HEX)
USERNAME_STYLE = getattr(TTkColor, config.sections["ui"].get("usernamestyle", "bold").upper().replace("NORMAL", "RST"))
USER_STATUS_COLORS = {
     UserStatus.ONLINE: TTkColor.fg(config.sections["ui"].get("useronline", "").upper() or "#16BB5C"),
     UserStatus.AWAY: TTkColor.fg(config.sections["ui"].get("useraway", "").upper() or "#C9AE13"),
     UserStatus.OFFLINE: TTkColor.fg(config.sections["ui"].get("useroffline", "").upper() or "#E04F5E")
}
USER_STATUS_ICONS = {
    UserStatus.ONLINE: TTkString(" ● ", USER_STATUS_COLORS[UserStatus.ONLINE]),   # "nplus-status-available",
    UserStatus.AWAY: TTkString(" ◑ ", USER_STATUS_COLORS[UserStatus.AWAY]),       # "nplus-status-away",
    UserStatus.OFFLINE: TTkString(" ◎ ", USER_STATUS_COLORS[UserStatus.OFFLINE])  # "nplus-status-offline"
}
USER_STATUS_LABELS = {
    UserStatus.ONLINE: _("Online"),
    UserStatus.AWAY: _("Away"),
    UserStatus.OFFLINE: _("Offline")
}
