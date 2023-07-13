# COPYRIGHT (C) 2020-2023 Nicotine+ Contributors
# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2016 Mutnick <muhing@yahoo.com>
# COPYRIGHT (C) 2013 eLvErDe <gandalf@le-vert.net>
# COPYRIGHT (C) 2008-2012 quinox <quinox@users.sf.net>
# COPYRIGHT (C) 2009 hedonist <ak@sensi.org>
# COPYRIGHT (C) 2006-2009 daelstorm <daelstorm@gmail.com>
# COPYRIGHT (C) 2003-2004 Hyriand <hyriand@thegraveyard.org>
# COPYRIGHT (C) 2001-2003 Alexander Kanavin
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

""" This module contains classes that deal with file transfers:
the transfer manager.
"""

import json
import os
import os.path
import re
import time

from ast import literal_eval
from collections import deque

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import encode_path
from pynicotine.utils import load_file
from pynicotine.utils import write_file_and_backup


class Transfer:
    """ This class holds information about a single transfer """

    __slots__ = ("sock", "user", "filename",
                 "path", "token", "size", "file", "start_time", "last_update",
                 "current_byte_offset", "last_byte_offset", "speed", "time_elapsed",
                 "time_left", "modifier", "queue_position", "file_attributes",
                 "iterator", "status", "legacy_attempt", "size_changed")

    def __init__(self, user=None, filename=None, path=None, status=None, token=None, size=0,
                 current_byte_offset=None, file_attributes=None):
        self.user = user
        self.filename = filename
        self.path = path
        self.size = size
        self.status = status
        self.token = token
        self.current_byte_offset = current_byte_offset
        self.file_attributes = file_attributes or {}

        self.sock = None
        self.file = None
        self.queue_position = 0
        self.modifier = None
        self.start_time = None
        self.last_update = None
        self.last_byte_offset = None
        self.speed = None
        self.time_elapsed = 0
        self.time_left = None
        self.iterator = None
        self.legacy_attempt = False
        self.size_changed = False


class Transfers:
    """ This is the transfers manager """

    def __init__(self):

        self.downloads_manager = None
        self.uploads_manager = None

        self.downloads = deque()
        self.uploads = deque()

        self.allow_saving_transfers = False
        self.upload_speed = 0  # self.uploads_manager.upload_speed
        self.token = 0

        self._transfer_timeout_timer_id = None

        for event_name, callback in (
            ("peer-connection-error", self._peer_connection_error),
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("start", self._start),
            ("transfer-request", self._transfer_request),
            ("user-stats", self._user_stats)
        ):
            events.connect(event_name, callback)

    def _start(self):

        from pynicotine.downloads import Downloads
        from pynicotine.uploads import Uploads

        self.downloads_manager = Downloads()
        self.uploads_manager = Uploads()

        self.downloads_manager.init_downloads(self.downloads)
        self.uploads_manager.init_uploads(self.uploads)

        self.add_stored_transfers("downloads")
        self.add_stored_transfers("uploads")

        self.allow_saving_transfers = True

        # Save list of transfers every minute
        events.schedule(delay=60, callback=self.save_transfers, repeat=True)

    def _quit(self):

        self.save_transfers()
        self.allow_saving_transfers = False

        self.downloads.clear()
        self.uploads.clear()

        self.upload_speed = 0
        self.token = 0

    def _server_login(self, msg):

        if not msg.success:
            return

        # Every 1 second: Check for transfer timeouts
        self._transfer_timeout_timer_id = events.schedule(
            delay=1,
            callback=self._check_transfer_timeouts,
            repeat=True
        )

    def _server_disconnect(self, _msg):
        events.cancel_scheduled(self._transfer_timeout_timer_id)

    """ Load Transfers """

    @staticmethod
    def load_transfers_file(transfers_file):
        """ Loads a file of transfers in json format """

        def json_keys_to_integer(dictionary):
            # JSON stores file attribute types as strings, convert them back to integers
            try:
                return {int(k): v for k, v in dictionary}

            except ValueError:
                return dictionary

        transfers_file = encode_path(transfers_file)

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, encoding="utf-8") as handle:
            return json.load(handle, object_pairs_hook=json_keys_to_integer)

    @staticmethod
    def load_legacy_transfers_file(transfers_file):
        """ Loads a download queue file in pickle format (legacy) """

        transfers_file = encode_path(transfers_file)

        if not os.path.isfile(transfers_file):
            return None

        with open(transfers_file, "rb") as handle:
            from pynicotine.utils import RestrictedUnpickler
            return RestrictedUnpickler(handle, encoding="utf-8").load()

    def load_transfers(self, transfer_type):

        load_func = self.load_transfers_file

        if transfer_type == "uploads":
            transfers_file = self.uploads_manager.get_upload_list_file_name()
        else:
            transfers_file = self.downloads_manager.get_download_queue_file_name()

        if transfer_type == "downloads" and not transfers_file.endswith("downloads.json"):
            load_func = self.load_legacy_transfers_file

        return load_file(transfers_file, load_func)

    def _load_file_attributes(self, num_attributes, transfer_row):

        if num_attributes < 7:
            return None

        loaded_file_attributes = transfer_row[6]

        if not loaded_file_attributes:
            return None

        if isinstance(loaded_file_attributes, dict):
            # Found dictionary with file attributes (Nicotine+ >=3.3.0), nothing more to do
            return loaded_file_attributes

        try:
            # Check if a dictionary is represented in string format
            return {int(k): v for k, v in literal_eval(loaded_file_attributes).items()}

        except (AttributeError, ValueError):
            pass

        # Legacy bitrate/duration strings (Nicotine+ <3.3.0)
        file_attributes = {}
        bitrate = str(loaded_file_attributes)
        is_vbr = (" (vbr)" in bitrate)

        try:
            file_attributes[slskmessages.FileAttribute.BITRATE] = int(bitrate.replace(" (vbr)", ""))

            if is_vbr:
                file_attributes[slskmessages.FileAttribute.VBR] = int(is_vbr)

        except ValueError:
            # No valid bitrate value found
            pass

        if num_attributes < 8:
            return file_attributes

        loaded_length = str(transfer_row[7])

        if ":" not in loaded_length:
            return file_attributes

        # Convert HH:mm:ss to seconds
        seconds = 0

        for part in loaded_length.split(":"):
            seconds = seconds * 60 + int(part, 10)

        file_attributes[slskmessages.FileAttribute.DURATION] = seconds

        return file_attributes

    def add_stored_transfers(self, transfer_type):

        transfers = self.load_transfers(transfer_type)

        if not transfers:
            return

        if transfer_type == "uploads":
            transfer_list = self.uploads
        else:
            transfer_list = self.downloads

        for transfer_row in transfers:
            num_attributes = len(transfer_row)

            if num_attributes < 3:
                continue

            # User / filename / path
            user = transfer_row[0]

            if not isinstance(user, str):
                continue

            filename = transfer_row[1]

            if not isinstance(filename, str):
                continue

            path = transfer_row[2]

            if not isinstance(path, str):
                continue

            if path:
                path = os.path.normpath(path)

            # Status
            loaded_status = None

            if num_attributes >= 4:
                loaded_status = str(transfer_row[3])

            if transfer_type == "uploads" and loaded_status != "Finished":
                # Only finished uploads are supposed to be restored
                continue

            if loaded_status in ("Aborted", "Paused"):
                status = "Paused"

            elif loaded_status in ("Filtered", "Finished"):
                status = loaded_status

            else:
                status = "User logged off"

            # Size / offset
            size = 0
            current_byte_offset = None

            if num_attributes >= 5:
                loaded_size = transfer_row[4]

                if loaded_size and isinstance(loaded_size, (int, float)):
                    size = int(loaded_size)

            if num_attributes >= 6:
                loaded_byte_offset = transfer_row[5]

                if loaded_byte_offset and isinstance(loaded_byte_offset, (int, float)):
                    current_byte_offset = int(loaded_byte_offset)

            # File attributes
            file_attributes = self._load_file_attributes(num_attributes, transfer_row)

            transfer_list.appendleft(
                Transfer(
                    user=user, filename=filename, path=path, status=status, size=size,
                    current_byte_offset=current_byte_offset, file_attributes=file_attributes
                )
            )

    """ File Actions """

    @staticmethod
    def close_file(file_handle, transfer):

        transfer.file = None

        if file_handle is None:
            return

        try:
            file_handle.close()

        except Exception as error:
            log.add_transfer("Failed to close file %(filename)s: %(error)s", {
                "filename": file_handle.name.decode("utf-8", "replace"),
                "error": error
            })

    """ Limits """

    def allow_new_uploads(self):
        return self.uploads_manager.allow_new_uploads()

    def update_upload_limits(self):
        self.uploads_manager.update_upload_limits()

    def update_download_limits(self):
        self.downloads_manager.update_download_limits()

    """ Events """

    def _user_stats(self, msg):
        """ Server code: 36 """

        if msg.user == core.login_username:
            self.upload_speed = msg.avgspeed

    def _peer_connection_error(self, user, msgs=None, is_offline=False):

        if msgs is None:
            return

        for i in msgs:
            if i.__class__ in (slskmessages.TransferRequest, slskmessages.FileUploadInit):
                self.uploads_manager.cant_connect_upload(user, i.token, is_offline)

            elif i.__class__ is slskmessages.QueueUpload:
                self.downloads_manager.cant_connect_queue_file(user, i.file, is_offline)

    def _transfer_request(self, msg):
        """ Peer code: 40 """

        user = msg.init.target_user

        if msg.direction == slskmessages.TransferDirection.UPLOAD:
            response = self.downloads_manager.transfer_request(msg)

            log.add_transfer(("Responding to download request with token %(token)s for file %(filename)s "
                              "from user: %(user)s, allowed: %(allowed)s, reason: %(reason)s"), {
                "token": response.token, "filename": msg.file, "user": user,
                "allowed": response.allowed, "reason": response.reason
            })

        elif msg.direction == slskmessages.TransferDirection.DOWNLOAD:
            response = self.uploads_manager.transfer_request(msg)

            if response is None:
                return

            log.add_transfer(("Responding to legacy upload request %(token)s for file %(filename)s "
                              "from user %(user)s, allowed: %(allowed)s, reason: %(reason)s"), {
                "token": response.token, "filename": msg.file, "user": user,
                "allowed": response.allowed, "reason": response.reason
            })

        else:
            log.add_transfer(("Received unknown transfer direction %(direction)s for file %(filename)s "
                              "from user %(user)s"), {
                "direction": msg.direction, "filename": msg.file, "user": user
            })
            return

        core.send_message_to_peer(user, response)

    def transfer_timeout(self, transfer):

        log.add_transfer("Transfer %(filename)s with token %(token)s for user %(user)s timed out", {
            "filename": transfer.filename,
            "token": transfer.token,
            "user": transfer.user
        })

        core.watch_user(transfer.user)

    """ Download Transfer Actions """

    def get_folder(self, *args):
        self.downloads_manager.get_folder(*args)

    def get_file(self, *args, **kwargs):
        self.downloads_manager.get_file(*args, **kwargs)

    def get_folder_destination(self, *args, **kwargs):
        return self.downloads_manager.get_folder_destination(*args, **kwargs)

    def get_current_download_file_path(self, *args):
        return self.downloads_manager.get_current_download_file_path(*args, **kwargs)

    def retry_downloads(self, *args):
        self.downloads_manager.retry_downloads(*args)

    def abort_downloads(self, *args, **kwargs):
        self.downloads_manager.abort_downloads(*args, **kwargs)

    def clear_downloads(self, *args, **kwargs):
        self.downloads_manager.clear_downloads(*args, **kwargs)

    """ Upload Transfer Actions """

    def push_file(self, *args, **kwargs):
        self.uploads_manager.push_file(*args, **kwargs)

    def get_total_uploads_allowed(self):
        return self.uploads_manager.get_total_uploads_allowed()

    def get_upload_queue_size(self, username=None):
        return self.uploads_manager.get_upload_queue_size(username)

    def get_downloading_users(self):
        return self.uploads_manager.get_downloading_users()

    def retry_uploads(self, *args):
        self.uploads_manager.retry_uploads(*args)

    def abort_uploads(self, *args, **kwargs):
        self.uploads_manager.abort_uploads(*args, **kwargs)

    def clear_uploads(self, *args, **kwargs):
        self.uploads_manager.clear_uploads(*args, **kwargs)

    def ban_users(self, *args, **kwargs):
        self.uploads_manager.ban_users(*args, **kwargs)

    def check_upload_queue(self):
        self.uploads_manager.check_upload_queue()

    def _check_transfer_timeouts(self):
        # When our port is closed, certain clients can take up to ~30 seconds before they
        # initiate a 'F' connection, since they only send an indirect connection request after
        # attempting to connect to our port for a certain time period.
        # Known clients: Nicotine+ 2.2.0 - 3.2.0, 2 s; Soulseek NS, ~20 s; soulseeX, ~30 s.
        # To account for potential delays while initializing the connection, add 15 seconds
        # to the timeout value.

        self.downloads_manager.check_download_timeouts(timeout=45)
        self.uploads_manager.check_upload_timeouts(timeout=45)

    """ Filters """

    def update_download_filters(self):
        self.downloads_manager.update_download_filters()

    """ Saving """

    def save_transfers(self):
        """ Save list of transfers """

        if not self.allow_saving_transfers:
            # Don't save if transfers didn't load properly!
            return

        config.create_data_folder()

        for transfers_file, callback in (
            (self.downloads_manager.get_download_queue_file_name(), self.downloads_manager.save_downloads_callback),
            (self.uploads_manager.get_upload_list_file_name(), self.uploads_manager.save_uploads_callback)
        ):
            write_file_and_backup(transfers_file, callback)
