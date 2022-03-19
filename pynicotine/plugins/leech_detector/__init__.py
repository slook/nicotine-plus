# COPYRIGHT (C) 2020-2021 Nicotine+ Team
# COPYRIGHT (C) 2011 Quinox <quinox@users.sf.net>
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

from pynicotine import slskmessages
from pynicotine.pluginsystem import BasePlugin


class Plugin(BasePlugin):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.settings = {
            'message': 'Please consider sharing more files if you would like to download from me again. Thanks :)',
            'num_files': 10,
            'num_folders': 1,
            'num_tolerate': 20,
            'send_minimums': True,
            'chk_zero_browse': True,
            'open_private_chat': True
        }
        self.metasettings = {
            'num_tolerate': {
                'description': 'Maximum number of leeched downloads to tolerate before complaining:',
                'type': 'int', 'minimum': 0, 'maximum': 999
            },
            'message': {
                'description': ('Automatically send a private chat message to leechers. '
                                'Each new line is sent as a separate message, '
                                'too many message lines may get you temporarily banned for spam!'),
                'type': 'textview'
            },
            'send_minimums': {
                'description': 'Notify leechers about the required minimums (creates an additional message line)',
                'type': 'bool'
            },
            'num_files': {
                'description': 'Require users to have a minimum number of shared files:',
                'type': 'int', 'minimum': 1
            },
            'num_folders': {
                'description': 'Require users to have a minimum number of shared folders:',
                'type': 'int', 'minimum': 1
            },
            'chk_zero_browse': {
                'description': 'Only send message to leechers with zero numbers if this can be verified',
                'type': 'bool'
            },
            'open_private_chat': {
                'description': 'Open private chat tabs when sending messages to leechers',
                'type': 'bool'
            }
        }

        self.count = {}

    def loaded_notification(self):

        self.check_thresholds()

        if self.settings['message'] or self.settings['send_minimums']:
            self.str_log_start = "complain to leecher"
        else:
            self.str_log_start = "log leecher"

        self.log(
            "Ready to %ss after tolerating %d downloads, "
            "require users have minimum %d files in %d shared public folders.",
            (self.str_log_start, self.settings['num_tolerate'],
             self.settings['num_files'], self.settings['num_folders'])
        )

    def check_thresholds(self):

        min_num_files = self.metasettings['num_files']['minimum']
        min_num_folders = self.metasettings['num_folders']['minimum']
        max_num_tolerate = self.metasettings['num_tolerate']['maximum']

        if self.settings['num_files'] < min_num_files:
            self.settings['num_files'] = min_num_files

        if self.settings['num_folders'] < min_num_folders:
            self.settings['num_folders'] = min_num_folders

        if self.settings['num_tolerate'] > max_num_tolerate:
            self.settings['num_tolerate'] = max_num_tolerate

    def upload_queued_notification(self, user, *_):

        if user in self.count:
            # We already have statistics for this user
            return

        self.count[user] = {
            'probed': 0,
            'uploaded': 0,
            'complained': 0,
            'leecher': False,
            'files': None,
            'dirs': None
        }

        self.log("Requesting statistics for new user %s...", user)

        self.core.queue.append(slskmessages.GetUserStats(user))

    def user_stats_notification(self, user, stats):

        if user not in self.count:
            # We did not trigger this notification
            return

        self.count[user]['probed'] += 1

        self.count[user]['files'] = stats['files']
        self.count[user]['dirs'] = stats['dirs']

        if self.count[user]['probed'] > 1:
            # User already logged
            return

        self.count[user]['leecher'] = self.is_leecher(user, log=False)

        if self.count[user]['leecher'] is False:
            self.log("New user %s has %d files in %d shared public folders available.",
                     (user, self.count[user]['files'], self.count[user]['dirs']))
            return

        self.log("New leecher %s has only %d files in %d shared public folders. "
                 "A maximum of %d leeches will be tolerated, then %s.",
                 (user, self.count[user]['files'], self.count[user]['dirs'],
                  self.settings['num_tolerate'], self.str_log_start))

    def is_leecher(self, user, log=True):

        if self.count[user]['files'] is None or self.count[user]['dirs'] is None:
            # Maybe upload finished before GetUserStats returned, too late
            return False

        if (self.count[user]['files'] >= self.settings['num_files'] and
            self.count[user]['dirs'] >= self.settings['num_folders']):

            if log:
                self.log("User %s finished %d downloads, has %s files in %s shared public folders available. Okay.",
                         (user, self.count[user]['uploaded'], self.count[user]['files'], self.count[user]['dirs']))

            return False  # User has required minimums, not a Leecher

        if user in (i[0] for i in self.config.sections["server"]["userlist"]):

            if log:
                self.log("Buddy %s leeched %d downloads, has only %s files in %s shared public folders available.",
                         (user, self.count[user]['uploaded'], self.count[user]['files'], self.count[user]['dirs']))

            return False  # Buddy will be logged but won't be sent any complaints

        if (self.count[user]['files'] == 0 and self.count[user]['dirs'] == 0):

            if log:
                self.log("User %s seems to have no public shares (zero, according to the server).", user)

            if self.settings['chk_zero_browse']:
                ## ToDo: Implement alternate fallback method (num_files | num_folders) from User Browse (Issue #1565) ##
                self.str_log_start = "log leecher"
                return False

        if not self.settings['message'] and self.settings['send_minimums'] == False:
            # No complaint message set, log only

            if log:
                self.log("Leecher %s finished %d downloads, has only %s files in %s shared public folders available."
                         "Not complaining because no chat message is configured in the plugin Properties.",
                         (user, self.count[user]['uploaded'], self.count[user]['files'], self.count[user]['dirs']))

            self.str_log_start = "log leecher"

        return True  # Leecher detected

    def upload_finished_notification(self, user, *_):

        if user not in self.count:
            return

        self.count[user]['uploaded'] += 1

        self.check_thresholds()  # incase the plugin Properties were recently changed

        if self.count[user]['uploaded'] > self.settings['num_tolerate']:
            return

        elif self.count[user]['uploaded'] < self.settings['num_tolerate']:
            return

        elif self.count[user]['uploaded'] == self.settings['num_tolerate']:
            # Reached the set tolerance threshold, now verify leeching then complain

            self.count[user]['leecher'] = self.is_leecher(user)

            if self.count[user]['leecher']:
                self.send_complaint(user)

        self.count[user]['files'] = self.count[user]['dirs'] = None  # clean up data we don't need anymore, finished.

    def send_complaint(self, user):

        if self.count[user]['complained'] >= 1 or self.count[user]['leecher'] is False:
            # We already dealt with this user, or they are not leeching
            return False

        if self.settings['send_minimums']:

            str_minimums = (
                "After %d downloads, this Leech Detector requires you have at least %d files "
                "in %d public shared folders (counted only %d files in %d folders)."
                % (self.count[user]['uploaded'], self.settings["num_files"], self.settings["num_folders"],
                   self.count[user]['files'], self.count[user]['dirs'])
            )

            # Notify leecher about our required minimums
            self.send_private(user, str_minimums, show_ui=self.settings["open_private_chat"], switch_page=False)

            self.count[user]['complained'] += 1

        # Send custom Private Chat Message to Leecher
        for line in self.settings['message'].splitlines():
            self.send_private(user, line, show_ui=self.settings['open_private_chat'], switch_page=False)

            self.count[user]['complained'] += 1

        self.log(
            "User %s leeched %d downloads, has only %d files in %d shared public folders. "
            "%d complaint message lines sent to leecher!",
            (user, self.count[user]['uploaded'], self.count[user]['files'], self.count[user]['dirs'],
             self.count[user]['complained'])
        )
