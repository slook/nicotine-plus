# COPYRIGHT (C) 2021-2022 Nicotine+ Contributors
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


""" Console Dialog Prompts """


class MessageDialog(Window):

    active_dialog = None  # Class variable keeping the dialog object alive

    def __init__(self, parent, title, message, callback=None, callback_data=None,
                 message_type=Gtk.MessageType.OTHER, buttons=None, width=-1):
        pass


class EntryDialog(MessageDialog):

    def __init__(self, parent, title, callback, message=None, callback_data=None, default="", use_second_entry=False,
                 second_default="", option_label="", option_value=False, visibility=True,
                 droplist=None, second_droplist=None):
        pass

class OptionDialog(MessageDialog):

    def __init__(self, parent, title, message, callback, callback_data=None, option_label="", option_value=False,
                 first_button=_("_No"), second_button=_("_Yes"), third_button="", fourth_button=""):

        buttons = []

        if first_button:
            buttons.append((first_button, 1))

        if second_button:
            buttons.append((second_button, 2))

        if third_button:
            buttons.append((third_button, 3))

        if fourth_button:
            buttons.append((fourth_button, 4))

        super().__init__(parent=parent, title=title, message=message, message_type=Gtk.MessageType.OTHER,
                         callback=callback, callback_data=callback_data, buttons=buttons)

        self.option = Gtk.CheckButton(label=option_label, active=option_value, visible=bool(option_label))

        if option_label:
            if GTK_API_VERSION >= 4:
                self.container.append(self.option)
            else:
                self.container.add(self.option)

    def prompt_confirm(title="", message="", confirm_keys="y Y q Q", decline_keys=None):
        """ Get keyboard input without needing to press the Enter key to submit.
        If decline_keys is None then the prompt can be dismissed with any key """

        import sys
        import termios
        import tty

        print(title.center(len(message)))
        print("+" * len(message)))

        buf = ""
        confirm = None

        stdin = sys.stdin.fileno()
        tattr = termios.tcgetattr(stdin)

        try:
            tty.setcbreak(stdin, termios.TCSANOW)

            while True:
                sys.stdout.write(f"{message}\nChoose {choices} >")
                sys.stdout.flush()

                buf += sys.stdin.read(1).lower()

                sys.stdout.write(buf[-1])

                if buf[-1] in confirm_keys:
                    confirm = True
                    break

                elif decline_keys is None or buf[-1] in decline_keys:
                    break

        finally:
            termios.tcsetattr(stdin, termios.TCSANOW, tattr)

        print("< Confirmed" if confirm else "< Cancelled")

        return confirm
