# COPYRIGHT (C) 2020-2022 Nicotine+ Team
# COPYRIGHT (C) 2008-2011 Quinox <quinox@users.sf.net>
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

from pynicotine.pluginsystem import BasePlugin, ResponseThrottle, returncode


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'public_default': False,
            'public_rooms': []
            #'private_default': False,
            #'private_users': [],
        }
        self.metasettings = {
            'public_default': {
                'description': 'Button toggled on by default in new Public Chats',
                'type': 'bool'
            }
            #'public_default': {
            #    'description': 'Button toggled on by default in new Private Chats',
            #    'type': 'bool'
            #},
        }
        self.__publiccommands__ = self.__privatecommands__ = [('button', self.port_checker_command)]

        self.visible_public = self.visible_private = True

        self.icon = self.icon_active = "add"
        self.tooltip = "Chat Button"
        self.label = ""

    def loaded_notification(self):
        #self.active_private = self.settings['public_default']

        # TODO: Per user show_privatechat_notification()
        pass


    def join_chatroom_notification(self, room):
        self.active_public = self.settings['public_default']

        # create_chat_button_widget(room)

    def leave_chatroom_notification(self, room):
        # remove_chat_button_widget(room)

        pass

    def incoming_public_chat_notification(self, room, user, line):
        if self.active_public:
            self.log("Chat Button is on and new message in Public Chat room %s", room)

    def incoming_private_chat_notification(self, user, line):
        if self.active_private:
            self.log("Chat Button is on and new message in Private Chat from user %s", user)

    def on_button_toggled(self, widget):
        # TODO: Get emitted toggle event
        # TODO: Get parent room tab or user tab name
        pass

    def chat_button_command(self, _, arg):

        if arg == "on":
            self.button_toggled(True)
        if arg == "off":
            self.button_toggled(False)
        else:
            self.button_toggled(not

        return returncode['zap']
