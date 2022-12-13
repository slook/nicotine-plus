# COPYRIGHT (C) 2022 Nicotine+ Contributors
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.commands = {
            "help": {
                "aliases": ["?"],
                "callback": self.help_command,
                "description": "List commands",
                "usage": ["[query]"]
            },
            "rescan": {
                "callback": self.rescan_command,
                "description": _("Rescan shares"),
                "group": _("Shares"),
                "usage": ["[-force]", ""]
            },
            "hello": {
                "aliases": ["echo", "greet"],
                "callback": self.hello_command,
                "description": "Print something",
                "group": _("Message"),
                "usage": ["[something..]"]
            },
            "away": {
                "aliases": ["a"],
                "callback": self.away_command,
                "description": _("Toggle away status")
            },
            "quit": {
                "aliases": ["q", "exit"],
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "usage": ["[-force]", ""]  # "" disallow extra args
            },
            "clear": {
                "aliases": ["cl"],
                "callback": self.clear_command,
                "description": _("Clear chat window"),
                "disable": ["cli"],
                "group": _("Chat"),
                "usage": [""]  # "" disallow any args
            },
            "join": {
                "aliases": ["j"],
                "callback": self.join_chat_command,
                "description": _("Join chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage": ["<room>"]
            },
            "me": {
                "callback": self.me_chat_command,
                "description": _("Say something in the third-person"),
                "disable": ["cli"],
                "group": _("Chat"),
                "usage": ["<something..>"]
            },
            "msg": {
                "aliases": ["m"],
                "callback": self.msg_chat_command,
                "description": _("Send private message to user"),
                "disable": ["cli"],
                "group": _("Private Chat"),
                "usage": ["<user>", "<message..>"]
            },
            "pm": {
                "callback": self.pm_chat_command,
                "description": _("Open private chat window for user"),
                "disable": ["cli"],
                "group": _("Private Chat"),
                "usage": ["<user>"],
            },
            "say": {
                "callback": self.say_chat_command,
                "description": _("Say message in specified chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage": ["<room>", "<message..>"]
            },

            "ctcpversion": {
                "callback": self.ctcpversion_command,
                "description": _("Ask for a user's client version"),
                "disable": ["cli"],
                "group": _("Chat"),
                "usage": ["[user]"],
            },

            "ipignore": {  # new
                "callback": self.ignore_ip_command,
                "description": _("Silence chat from anyone at IP address"),
                "disable": ["cli"],
                "group": _("Network Filters"),
                "usage": ["<ip_address>"]
            },
            "ipunignore": {  # new
                "callback": self.unignore_ip_command,
                "description": _("Remove IP address from chat ignore list"),
                "disable": ["cli"],
                "group": _("Network Filters"),
                "usage": ["<ip_address>"]
            },

            "close": {
                "aliases": ["c"],
                "callback": self.close_command,
                "description": _("Close private chat"),
                "disable": ["cli"],
                "group": _("Private Chat"),
                "usage_chatroom": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "leave": {
                "aliases": ["l"],
                "callback": self.leave_command,
                "description": _("Leave chat room"),
                "disable": ["cli"],
                "group": _("Chat Rooms"),
                "usage_chatroom": ["[room]"],
                "usage_private_chat": ["<room>"],
            },
            "add": {
                "aliases": ["buddy"],
                "callback": self.add_buddy_command,
                "description": _("Add user to buddy list"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "rem": {
                "aliases": ["unbuddy"],
                "callback": self.remove_buddy_command,
                "description": _("Remove user from buddy list"),
                "group": _("Users"),
                "usage_chatroom": ["<buddy>"],
                "usage_private_chat": ["[buddy]"]
            },
            "ban": {
                "callback": self.ban_user_command,
                "description": _("Stop connections from user"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "unban": {
                "callback": self.unban_user_command,
                "description": _("Remove user from ban list"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "block": {  # new
                "callback": self.block_user_ip_command,
                "description": _("Stop all connections from same IP as user"),
                "group": _("Network Filters"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "unblock": {  # new
                "callback": self.unblock_user_ip_command,
                "description": _("Remove user's IP address from block list"),
                "group": _("Network Filters"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "ignore": {
                "callback": self.ignore_user_command,
                "description": _("Silence chat messages from user"),
                "disable": ["cli"],
                "group": _("Users"),
                "usage_chatroom": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "unignore": {
                "callback": self.unignore_user_command,
                "description": _("Remove user from chat ignore list"),
                "disable": ["cli"],
                "group": _("Users"),
                "usage_chatroom": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "ignoreip": {
                "callback": self.ignore_user_ip_command,
                "description": _("Silence chat messages from IP address of user"),
                "disable": ["cli"],
                "group": _("Network Filters"),
                "usage_chatroom": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "unignoreip": {  # new
                "callback": self.unignore_user_ip_command,
                "description": _("Remove user's IP address from chat ignore list"),
                "disable": ["cli"],
                "group": _("Network Filters"),
                "usage_chatroom": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "ip": {
                "callback": self.ip_user_command,
                "description": _("Show IP address of user"),
                "group": _("Network Filters"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "whois": {
                "aliases": ["info"],
                "callback": self.whois_user_command,
                "description": _("Show info about user"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "browse": {
                "aliases": ["b"],
                "callback": self.browse_user_command,
                "description": _("Browse files of user"),
                "group": _("Users"),
                "usage": ["<user>"],
                "usage_private_chat": ["[user]"]
            },
            "listshares": {
                "callback": self.list_shares_command,
                "description": _("List shares"),
                "group": _("Shares")
            },
            "addshare": {
                "callback": self.add_share_command,
                "description": _("Add share"),
                "group": _("Shares"),
                "usage": ["<public|private|buddy>", "<\"virtual name\">", "<\"folder path\">", ""]  # "" max 3 args
            },
            "removeshare": {
                "callback": self.remove_share_command,
                "description": _("Remove share"),
                "group": _("Shares"),
                "usage": ["<public|private|buddy>", "<\"virtual name\">", ""]  # "" max 2 args (quotes not mandatory)
            }
        }

    def help_command(self, args, user=None, room=None):

        if user is not None:
            command_list = self.parent.private_chat_commands
            interface = "private_chat"  # _("_")
            prefix = "/"

        elif room is not None:
            command_list = self.parent.chatroom_commands
            interface = "chatroom"
            prefix = "/"

        else:
            command_list = self.parent.cli_commands
            interface = "cli"
            prefix = ""

        query = args.split(" ", maxsplit=1)[0].lower().lstrip("/")
        command_groups = {}
        num_commands = 0

        for command, data in command_list.items():
            command_message = command
            usage = " ".join(data.get("usage", []))
            aliases = f", {prefix}".join(data.get("aliases", []))

            if aliases:
                command_message += f", {prefix}" + aliases

            if usage:
                command_message += " " + usage

            if interface == "cli":
                # Improved layout for fixed width output
                command_message = command_message.ljust(24)

            description = data.get("description", "No description")
            group = data.get("group", f"{self.config.application_name} {_('Commands')}")

            if args and query not in command_message and query not in group.lower():
                continue

            num_commands += 1

            if interface == "cli":
                command_message = command_message.lstrip("/").ljust(24)

            if group not in command_groups:
                command_groups[group] = []

            command_groups[group].append("    %s  -  %s" % (command_message, description))

        if not num_commands:
            self.echo_unknown_command(query)
            return False

        output = f"Listing {num_commands} {interface} commands" + (" " + f"matching \"{query}\":" if query else ":")

        for group, commands in command_groups.items():
            output += "\n\n" + "  " + group + ":"

            for command in commands:
                output += "\n" + command

        output += "\n"

        if not query:
            output += "\n" + f"Type {prefix}help [query] (without brackets) to list similar commands or aliases"

        if prefix:
            output += "\n" + "Start a command using / (forward slash)"

        self.echo_message(output)
        return True

    """ "Chats" """

    def clear_command(self, _args, user=None, room=None):

        if room is not None:
            self.core.chatrooms.clear_messages(room)

        elif user is not None:
            self.core.privatechat.clear_private_messages(user)

    def close_command(self, args, user=None, **_unused):

        if args:
            user = args

        if user not in self.core.privatechat.users:
            self.echo_message("Not messaging with user %s" % user)
            return False

        self.echo_message("Closing private chat of user %s" % user)
        self.core.privatechat.remove_user(user)
        return True

    def ctcpversion_command(self, args, user=None, **_unused):

        if args:
            user = args

        elif user is None:
            user = self.core.login_username

        if self.send_private(user, self.core.privatechat.CTCP_VERSION, show_ui=False):
            self.echo_message("Asked %s for client version" % user)
            return True

        return False

    def hello_command(self, args, **_unused):
        self.echo_message("Hello there! %s" % args)

    def join_chat_command(self, args, **_unused):
        self.core.chatrooms.show_room(args)

    def leave_command(self, args, room=None, **_unused):

        if args:
            room = args

        if room not in self.core.chatrooms.joined_rooms:
            self.echo_message("Not joined in room %s" % room)
            return False

        self.core.chatrooms.remove_room(room)
        return True

    def me_chat_command(self, args, **_unused):
        return self.send_message("/me " + args)

    def msg_chat_command(self, args, **_unused):

        args_split = args.split(" ", maxsplit=1)
        user, text = args_split[0], args_split[1]

        if self.send_private(user, text, show_ui=True, switch_page=False):
            self.echo_message("Private message sent to user %s" % user)
            return True

        return False

    def pm_chat_command(self, args, **_unused):
        self.core.privatechat.show_user(args)
        self.log("Private chat with user %s" % args)

    def say_chat_command(self, args, **_unused):

        args_split = args.split(" ", maxsplit=1)
        room, text = args_split[0], args_split[1]

        if self.send_public(room, text):
            self.echo_message("Chat message sent to room %s" % room)
            return True

        return False

    """ "Shares" """

    def add_share_command(self, args, **_unused):

        from shlex import split  # support long arguments in quotes, needed here for <"virtual name">

        args_split = split(args)
        group, name, path = args_split[0], args_split[1], args_split[2]

        self.echo_message(f"nothing here yet, you entered: group='{group}' name='{name}' path='{path}'")

    def remove_share_command(self, args, **_unused):

        args_split = args.split(maxsplit=1)
        group, name = args_split[0], args_split[1].strip("\"' ")  # don't require quotes

        self.echo_message(f"nothing here yet, you entered: group='{group}' name='{name}'")

    def list_shares_command(self, _args, **_unused):
        # TODO: self.echo_message(self.core.shares.list_shares())
        self.echo_message("nothing here yet")

    def rescan_command(self, args, **_unused):

        force = bool("force" in args)

        self.core.shares.rescan_shares(force=force)

    """ "Users" """

    def add_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.userlist.add_user(user)

    def remove_buddy_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.userlist.remove_user(user)

    def ban_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.ban_user(user)

    def unban_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unban_user(user)

    def block_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.block_user_ip(user)

    def unblock_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unblock_user_ip(user)

    def ignore_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.ignore_user(user)

    def unignore_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unignore_user(user)

    def ignore_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.ignore_user_ip(user)

    def unignore_user_ip_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.network_filter.unignore_user_ip(user)

    def ip_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.request_ip_address(user)

    def ignore_ip_command(self, args, **_unused):
        return self.core.network_filter.ignore_ip(args)

    def unignore_ip_command(self, args, **_unused):
        # TODO: self.core.network_filter.unignore_ip(ip_address)
        self.echo_message(f"nothing here yet, you entered: {args}")

    def whois_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.userinfo.request_user_info(user)

    def browse_user_command(self, args, user=None, **_unused):

        if args:
            user = args

        return self.core.userbrowse.browse_user(user)

    """ General "Commands" """

    def away_command(self, _args, **_unused):
        self.core.set_away_mode(self.core.user_status != 1, save_state=True)  # 1 = UserStatus.AWAY
        self.echo_message("Status is now %s" % (_("Online") if self.core.user_status == 2 else _("Away")))

    def quit_command(self, args, user=None, room=None):

        if user is not None:
            interface = "private_chat"

        elif room is not None:
            interface = "chatroom"

        else:
            interface = "cli"

        if "force" not in args:
            self.log("Exiting application on %s command %s" % (interface, args))
            self.core.confirm_quit()
            return

        # TODO: quit only works with force due to no support for prompt in headless core
        self.log("Quitting on %s command %s" % (interface, args))
        self.core.quit()

    def shutdown_notification(self):
        self.log("Shutdown!")
