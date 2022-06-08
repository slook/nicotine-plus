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
        self.__publiccommands__ = [('rescan', self.rescan_command)]
        self.__privatecommands__ = self.__clicommands__ = [
            ('rescan', self.rescan_command),
            ('hello', self.hello_command)
        ]

    def rescan_command(self, _source, _args):
        self.core.shares.rescan_shares()
        return True

    def hello_command(self, _source, args):

        if args:
            self.echo_message("Hello there, %s" % args)
        else:
            self.echo_message("Provide a user name as parameter.")

        return True