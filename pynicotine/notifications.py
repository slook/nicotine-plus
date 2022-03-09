# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import threading

from pynicotine.logfacility import log
from pynicotine.utils import execute_command


class Notifications:

    def __init__(self, config, ui_callback=None):

        self.config = config
        self.ui_callback = None

        self.chat_hilites = {
            "rooms": [],
            "private": []
        }

        self.tts = []
        self.tts_playing = False
        self.continue_playing = False
        self.last_room = self.last_user = self.last_message = None

        if hasattr(ui_callback, "notifications"):
            self.ui_callback = ui_callback.notifications

    """ Chat Hilites """

    def add_hilite_item(self, location, item):

        if not item or item in self.chat_hilites[location]:
            return False

        self.chat_hilites[location].append(item)
        return True

    def remove_hilite_item(self, location, item):

        if item not in self.chat_hilites[location]:
            return False

        self.chat_hilites[location].remove(item)
        return True

    """ Text Notification """

    def new_text_notification(self, message, title=None):

        if self.ui_callback:
            self.ui_callback.new_text_notification(message, title)
            return

        if title:
            message = "%s: %s" % (title, message)

        log.add(message)

    """ TTS """

    def chat_tts(self, room=None, user=None, message=""):

        if not self.config.sections["ui"]["speechenabled"]:
            return

        if room:
            speech_format = self.config.sections["ui"]["speechrooms"]
            speech_map = {"room": room, "user": user, "message": message}
        else:
            speech_format = self.config.sections["ui"]["speechprivate"]
            speech_map = {"user": user, "message": message}

        if self.tts_playing and room == self.last_room:
            if user == self.last_user and message == self.last_message:
                return  # duplicated Public feed messages or cross-posted spam

            if user == self.last_user:
                # Consecutive multiline messages from same sender... : (message)
                speech_format = speech_format.split(":", maxsplit=1)[-1]
                if "%(message)s" not in speech_format:
                    speech_format = "%(user)s: %(message)s ... Text-To-Speech syntax! incorrect :"

            else:
                # Ongoing conversations in same room... , (user) said: (message)
                speech_format = speech_format.split(",", maxsplit=1)[-1]

            speech_map = {"user": user, "message": message}
            log.add_debug(message)

        self.new_tts(speech_format, speech_map)

        # Remember last source for clearer message format if queued tts_playing
        self.last_room, self.last_user, self.last_message = room, user, message

    def new_tts(self, message, args=None):

        if message in self.tts:
            return

        if args:
            for key, value in args.items():
                args[key] = self.tts_clean_message(value)

            try:
                message = message % args
            except (TypeError, NameError):
                log.add_debug("TTS error: Format syntax requires %(room)s, %(user)s: %(message)s")

        self.tts.append(message)

        if self.tts_playing:
            # Avoid spinning up useless threads
            self.continue_playing = True
            return

        thread = threading.Thread(target=self.play_tts)
        thread.name = "TTS"
        thread.daemon = True
        thread.start()

    def play_tts(self):

        for message in self.tts[:]:
            self.tts_player(message)

            if message in self.tts:
                self.tts.remove(message)

        self.tts_playing = False
        if self.continue_playing:
            self.continue_playing = False
            self.play_tts()

    @staticmethod
    def tts_clean_message(message):

        for i in ["_", "[", "]", "(", ")"]:
            message = message.replace(i, " ")

        return message

    def tts_player(self, message):

        self.tts_playing = True

        try:
            execute_command(self.config.sections["ui"]["speechcommand"], message, background=False)

        except Exception as error:
            log.add(_("Text-to-speech for message failed: %s"), str(error))
