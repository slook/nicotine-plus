# COPYRIGHT (C) 2022 Nicotine+ Team
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

        commands = {
            "help": {
                "callback": self.help_command,
                "description": "Show commands",
                "usage": ["[query]"],
                "aliases": ["?"]
            },
            "rescan": {
                "callback": self.rescan_command,
                "description": _("Rescan shares"),
                "group": _("Shares")
            },
            "hello": {
                "callback": self.hello_command,
                "description": "Print something",
                "usage": ["[something..]"],
                "aliases": ["echo", "greet"],
                "group": _("Message")
            },
            "away": {
                "callback": self.away_command,
                "description": _("Toggle away status"),
                "aliases": ["a"]
            },
            "quit": {
                "callback": self.quit_command,
                "description": _("Quit Nicotine+"),
                "usage": ["[force]"],
                "aliases": ["q", "exit"]
            }
        }

        chat_commands = {
            "clear": {
                "callback": self.clear_command,
                "description": _("Clear chat window"),
                "aliases": ["cl"],
                "group": _("Chat")
            },
            "close": {
                "callback": self.close_command,
                "description": _("Close private chat"),
                "usage": ["[user]"],
                "aliases": ["c"],
                "group": _("Private Chat")
            },
            "join": {
                "callback": self.join_command,
                "description": _("Join chat room"),
                "usage": ["<room>"],
                "aliases": ["j"],
                "group": _("Chat Rooms")
            },
            "leave": {
                "callback": self.leave_command,
                "description": _("Leave chat room"),
                "usage": ["[room]"],
                "aliases": ["l"],
                "group": _("Chat Rooms")
            },
            "me": {
                "callback": self.me_command,
                "description": _("Say something in the third-person"),
                "usage": ["<something..>"],
                "group": _("Chat")
            },
            "msg": {
                "callback": self.msg_command,
                "description": _("Send private message to user"),
                "usage": ["<user>", "<message..>"],
                "aliases": ["m"],
                "group": _("Private Chat")
            },
            "pm": {
                "callback": self.private_message_command,
                "description": _("Open private chat window for user"),
                "usage": ["<user>", "[message..]"],
                "group": _("Private Chat")
            },
            "say": {
                "callback": self.say_command,
                "description": _("Say message in specified chat room"),
                "usage": ["<room>", "<message..>"],
                "group": _("Chat Rooms")
            },
            "ctcpversion": {
                "callback": self.ctcpversion_command,
                "description": _("Ask for a user's client version"),
                "usage": ["[user]"],
                "group": _("Client-To-Client Protocol")
            }
        }

        cli_commands = {
            "addshare": {
                "callback": self.add_share_command,
                "description": _("Add share"),
                "usage": ["<public|private>", "<virtual_name>", "<path>"],
                "group": _("Shares")
            },
            "removeshare": {
                "callback": self.remove_share_command,
                "description": _("Remove share"),
                "usage": ["<public|private>", "<virtual_name>"],
                "group": _("Shares")
            },
            "listshares": {
                "callback": self.list_shares_command,
                "description": _("List shares"),
                "group": _("Shares")
            }
        }

        self.chatroom_commands = {**commands, **chat_commands}
        self.private_chat_commands = {**commands, **chat_commands}
        self.cli_commands = {**commands, **cli_commands}

    def help_command(self, args, command_type, _source):

        query = args.split(" ", maxsplit=1)[0].lower().lstrip("/")

        if command_type == "chatroom":
            command_list = self.parent.chatroom_commands

        elif command_type == "private_chat":
            command_list = self.parent.private_chat_commands

        elif command_type == "cli":
            command_list = self.parent.cli_commands

        command_groups = {}
        num_commands = 0

        for command, data in command_list.items():
            command_message = command
            usage = " ".join(data.get("usage", []))
            aliases = data.get("aliases", [])

            if aliases:
                command_message = command_message + " /" + " /".join(aliases)

            if usage:
                command_message += " " + usage

            description = data.get("description", "No description")
            group = data.get("group", _("Commands"))
            group_words = group.lower().split(" ")

            if not args or query in command or query in (a for a in aliases) or query in group_words:
                if group not in command_groups:
                    command_groups[group] = []

                command_groups[group].append("    %s  -  %s" % (command_message, description))
                num_commands += 1

        if not num_commands:
            self.echo_unknown_command(query)

        elif num_commands >= 2 and query:
            self.echo_message("List of %i commands matching \"%s\":" % (num_commands, query))

        for group, commands in command_groups.items():
            self.echo_message("")
            self.echo_message("  " + group + ":")

            for command in commands:
                self.echo_message(command)

    def _echo_missing_arg(self, arg):
        self.echo_message("Missing argument: %s" % arg)

    def _echo_unexpect_arg(self, arg):
        self.echo_message("Unexpected argument: %s" % arg.split(" ", maxsplit=1)[0])

    def close_command(self, args, command_type, source):

        user = args if args else (source if command_type == "private_chat" else None)
        echo = self.echo_message if user != source else self.log

        if user in self.core.privatechats.users:
            echo("Closing private chat of user %s" % user)
        elif user:
            echo("Not messaging with user %s" % user)
        else:
            self._echo_missing_arg('[user]')

        self.core.privatechats.remove_user(user)

    def clear_command(self, args, command_type, source):

        if args:
            self._echo_unexpect_arg(args)

        elif command_type == "chatroom":
            self.core.chatrooms.clear_messages(source)

        elif command_type == "private_chat":
            self.core.privatechats.clear_messages(source)

    def join_command(self, args, _command_type, _source):
        self.core.chatrooms.show_room(args)

    def leave_command(self, args, command_type, source):

        room = args if args else (source if command_type == "chatroom" else None)

        if not room:
            self._echo_missing_arg('[room]')
        elif room not in self.core.chatrooms.joined_rooms:
            self.echo_message("Not joined in room %s" % room)

        self.core.chatrooms.remove_room(room)

    def me_command(self, args, _command_type, _source):
        self.send_message("/me " + args)

    def msg_command(self, args, _command_type, _source):
        self.private_message_command(args, _command_type, _source, switch_page=False)

    def private_message_command(self, args, _command_type, _source, switch_page=True):

        args_split = args.split(" ", maxsplit=1)
        user, text = args_split[0], args_split[1] if len(args_split) == 2 else None

        if self.send_private(user, text, show_ui=True, switch_page=switch_page):
            if switch_page:
                self.log("Private chat with user %s" % user)
            else:
                self.log("Private message sent to user %s" % user)

    def rescan_command(self, _args, _command_type, _source):
        self.core.shares.rescan_shares()

    def say_command(self, args, _command_type, _source):

        args_split = args.split(" ", maxsplit=1)
        room, text = args_split[0], args_split[1]

        if self.send_public(room, text):
            self.log("Chat message sent to room %s" % room)

    def hello_command(self, args, _command_type, _source):
        self.echo_message("Hello there! %s" % args)

    def add_share_command(self, _args, _command_type, _source):

        # share_type, virtual_name, path = args.split(maxsplit=3)

        self.core.shares.rescan_shares()

    def remove_share_command(self, _args, _command_type, _source):

        # share_type, virtual_name, *_unused = args.split(maxsplit=2)

        self.core.shares.rescan_shares()

    def list_shares_command(self, _args, _command_type, _source):
        self.echo_message("nothing here yet")

    def away_command(self, _args, _command_type, _source):
        self.core.set_away_mode(self.core.user_status != 1, save_state=True)  # 1 = UserStatus.AWAY
        self.echo_message("Status is now %s" % (_("Online") if self.core.user_status == 2 else _("Away")))

    def ctcpversion_command(self, args, command_type, source):

        user = args if args else (source if command_type == "private_chat" else self.core.login_username)

        if self.send_private(user, self.core.privatechats.CTCP_VERSION, show_ui=False):
            self.echo_message("Asked %s for client version" % user)

    def quit_command(self, args, command_type, _source):

        if "force" not in args:
            self.log("Exiting application on %s command %s" % (command_type, args))
            self.core.confirm_quit()
            return

        self.log("Quitting on %s command %s" % (command_type, args))
        self.core.quit()

    def shutdown_notification(self):
        self.log("Shutdown!")