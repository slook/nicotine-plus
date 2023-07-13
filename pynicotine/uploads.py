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


import json
import os
import os.path
import re
import time

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.transfers import Transfer
from pynicotine.utils import encode_path
from pynicotine.utils import human_speed
from pynicotine.utils import write_file_and_backup


class Uploads():
    """ This is the uploads manager """

    def __init__(self):

        self.uploads = None
        self.upload_requests = {}
        self.privileged_users = set()
        # self.upload_speed = 0

        self.user_update_counter = 0
        self.user_update_counters = {}

        self._upload_queue_timer_id = None
        self._retry_failed_uploads_timer_id = None

        for event_name, callback in (
            ("add-privileged-user", self._add_to_privileged),
            ("file-upload-init", self._file_upload_init),
            ("file-upload-progress", self._file_upload_progress),
            ("place-in-queue-request", self._place_in_queue_request),
            ("queue-upload", self._queue_upload),
            ("quit", self._quit),
            ("remove-privileged-user", self._remove_from_privileged),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("start", self._start),
            ("transfer-response", self._transfer_response),
            ("upload-connection-closed", self._upload_connection_closed),
            ("upload-file-error", self._upload_file_error),
            ("user-status", self._user_status)
        ):
            events.connect(event_name, callback)

    def init_uploads(self, transfer_list):
        self.uploads = transfer_list

    def _start(self):

        self.update_upload_limits()

    def _quit(self):
        self.uploads.clear()
        # self.upload_speed = 0

    def _server_login(self, msg):

        if not msg.success:
            return

        self.update_upload_limits()

        # Every 10 seconds: Check if queued uploads can be started
        self._upload_queue_timer_id = events.schedule(
            delay=10,
            callback=self.check_upload_queue,
            repeat=True
        )

        # Every 3 minutes: Re-queue timed out uploads
        self._retry_failed_uploads_timer_id = events.schedule(
            delay=180,
            callback=self.retry_failed_uploads,
            repeat=True
        )

    def _server_disconnect(self, _msg):

        for timer_id in (self._upload_queue_timer_id, self._retry_failed_uploads_timer_id):
            events.cancel_scheduled(timer_id)

        need_update = False

        for upload in self.uploads.copy():
            if upload.status != "Finished":
                need_update = True
                self.clear_upload(upload, update_parent=False)

        if need_update:
            events.emit("update-uploads")

        self.privileged_users.clear()
        self.user_update_counters.clear()

        self.user_update_counter = 0

    """ Load Transfers """

    def get_upload_list_file_name(self):
        return os.path.join(config.data_dir, "uploads.json")

    @staticmethod
    def _get_file_size(filename):

        try:
            size = os.path.getsize(encode_path(filename))
        except Exception:
            # file doesn't exist (remote files are always this)
            size = 0

        return size

    """ Privileges """

    def _add_to_privileged(self, user):
        self.privileged_users.add(user)

    def _remove_from_privileged(self, user):
        if user in self.privileged_users:
            self.privileged_users.remove(user)

    def _is_privileged(self, user):

        if not user:
            return False

        if user in self.privileged_users:
            return True

        return self._is_buddy_prioritized(user)

    def _is_buddy_prioritized(self, user):

        user_data = core.userlist.buddies.get(user)

        if user_data:
            # All users
            if config.sections["transfers"]["preferfriends"]:
                return True

            # Only explicitly prioritized users
            return bool(user_data.is_prioritized)

        return False

    """ Limits """

    def update_upload_limits(self):

        events.emit("update-upload-limits")

        if core.user_status == slskmessages.UserStatus.OFFLINE:
            return

        use_speed_limit = config.sections["transfers"]["use_upload_speed_limit"]
        limit_by = config.sections["transfers"]["limitby"]

        if use_speed_limit == "primary":
            speed_limit = config.sections["transfers"]["uploadlimit"]

        elif use_speed_limit == "alternative":
            speed_limit = config.sections["transfers"]["uploadlimitalt"]

        else:
            speed_limit = 0

        core.queue.append(slskmessages.SetUploadLimit(speed_limit, limit_by))

    def _queue_limit_reached(self, user):

        file_limit = config.sections["transfers"]["filelimit"]
        queue_size_limit = config.sections["transfers"]["queuelimit"] * 1024 * 1024

        if not file_limit and not queue_size_limit:
            return False, None

        num_files = 0
        queue_size = 0

        for upload in self.uploads:
            if upload.user != user or upload.status != "Queued":
                continue

            if file_limit:
                num_files += 1

                if num_files >= file_limit:
                    return True, "Too many files"

            if queue_size_limit:
                queue_size += upload.size

                if queue_size >= queue_size_limit:
                    return True, "Too many megabytes"

        return False, None

    def _slot_limit_reached(self):

        upload_slot_limit = config.sections["transfers"]["uploadslots"]

        if upload_slot_limit <= 0:
            upload_slot_limit = 1

        num_in_progress = 0
        active_statuses = ("Getting status", "Transferring")

        for upload in self.uploads:
            if upload.status in active_statuses:
                num_in_progress += 1

                if num_in_progress >= upload_slot_limit:
                    return True

        return False

    def _bandwidth_limit_reached(self):

        bandwidth_limit = config.sections["transfers"]["uploadbandwidth"] * 1024

        if not bandwidth_limit:
            return False

        bandwidth_sum = 0

        for upload in self.uploads:
            if upload.sock is not None and upload.speed is not None:
                bandwidth_sum += upload.speed

                if bandwidth_sum >= bandwidth_limit:
                    return True

        return False

    def allow_new_uploads(self):

        if core.shares.rescanning:
            return False

        if config.sections["transfers"]["useupslots"]:
            # Limit by upload slots
            if self._slot_limit_reached():
                return False

        else:
            # Limit by maximum bandwidth
            if self._bandwidth_limit_reached():
                return False

        # No limits
        return True

    def _file_is_upload_queued(self, user, filename):

        statuses = ("Queued", "Getting status", "Transferring")

        return next(
            (upload.filename == filename and upload.status in statuses and upload.user == user
             for upload in self.uploads), False
        )

    @staticmethod
    def _file_is_readable(filename, real_path):

        try:
            if os.access(encode_path(real_path), os.R_OK):
                return True

            log.add_transfer("Cannot access file, not sharing: %(virtual_name)s with real path %(path)s", {
                "virtual_name": filename,
                "path": real_path
            })

        except Exception:
            log.add_transfer(("Requested file path contains invalid characters or other errors, not sharing: "
                              "%(virtual_name)s with real path %(path)s"), {
                "virtual_name": filename,
                "path": real_path
            })

        return False

    """ Events """

    def _user_status(self, msg):
        """ Server code: 7 """
        """ We get a status of a user and if he's online, we push a file to him """

        update = False
        username = msg.user
        privileged = msg.privileged
        user_offline = (msg.status == slskmessages.UserStatus.OFFLINE)
        upload_statuses = ("Getting status", "User logged off", "Connection timeout")

        if privileged is not None:
            if privileged:
                events.emit("add-privileged-user", username)
            else:
                events.emit("remove-privileged-user", username)

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for upload in reversed(self.uploads.copy()):
            if upload.user == username and upload.status in upload_statuses:
                if user_offline:
                    if not self._auto_clear_upload(upload):
                        upload.status = "User logged off"
                        self._abort_upload(upload, abort_reason=None)

                    update = True

                elif upload.status == "User logged off":
                    if not self._auto_clear_upload(upload):
                        upload.status = "Cancelled"

                    update = True

        if update:
            events.emit("update-uploads")

    def _connect_to_peer(self, msg):
        """ Server code: 18 """

        if msg.privileged is None:
            return

        if msg.privileged:
            events.emit("add-privileged-user", msg.user)
        else:
            events.emit("remove-privileged-user", msg.user)

    def cant_connect_upload(self, username, token, is_offline):
        """ We can't connect to the user, either way (TransferRequest, FileUploadInit). """

        for upload in self.uploads:
            if upload.token != token or upload.user != username:
                continue

            log.add_transfer("Upload attempt for file %(filename)s with token %(token)s to user %(user)s timed out", {
                "filename": upload.filename,
                "token": token,
                "user": username
            })

            if upload.sock is not None:
                log.add_transfer("Existing file connection for upload with token %s already exists?", token)
                return

            upload_cleared = is_offline and self._auto_clear_upload(upload)

            if not upload_cleared:
                self._abort_upload(upload, abort_reason="User logged off" if is_offline else "Connection timeout")

            core.watch_user(username)
            self.check_upload_queue()
            return

    def _queue_upload(self, msg):
        """ Peer code: 43 """
        """ Peer remotely queued a download (upload here). This is the modern replacement to
        a TransferRequest with direction 0 (download request). We will initiate the upload of
        the queued file later. """

        user = msg.init.target_user
        filename = msg.file

        log.add_transfer("Received upload request for file %(filename)s from user %(user)s", {
            "user": user,
            "filename": filename,
        })

        real_path = core.shares.virtual2real(filename)
        allowed, reason = self._check_queue_upload_allowed(user, msg.init.addr, filename, real_path, msg)

        log.add_transfer(("Upload request for file %(filename)s from user: %(user)s, "
                          "allowed: %(allowed)s, reason: %(reason)s"), {
            "filename": filename,
            "user": user,
            "allowed": allowed,
            "reason": reason
        })

        if not allowed:
            if reason and reason != "Queued":
                core.send_message_to_peer(user, slskmessages.UploadDenied(file=filename, reason=reason))

            return

        transfer = Transfer(user=user, filename=filename, path=os.path.dirname(real_path),
                            status="Queued", size=self._get_file_size(real_path))
        self._append_upload(user, filename, transfer)
        self._update_upload(transfer)

        core.pluginhandler.upload_queued_notification(user, filename, real_path)
        self.check_upload_queue()

    def transfer_request(self, msg):
        """ Remote peer is requesting to download a file through your upload queue.
        Note that the QueueUpload peer message has replaced this method of requesting
        a download in most clients. """

        user = msg.init.target_user
        filename = msg.file
        token = msg.token

        log.add_transfer("Received legacy upload request %(token)s for file %(filename)s from user %(user)s", {
            "token": token,
            "filename": filename,
            "user": user
        })

        # Is user allowed to download?
        real_path = core.shares.virtual2real(filename)
        allowed, reason = self._check_queue_upload_allowed(user, msg.init.addr, filename, real_path, msg)

        if not allowed:
            if reason:
                return slskmessages.TransferResponse(allowed=False, reason=reason, token=token)

            return None

        # All checks passed, user can queue file!
        core.pluginhandler.upload_queued_notification(user, filename, real_path)

        # Is user already downloading/negotiating a download?
        already_downloading = False
        active_statuses = ("Getting status", "Transferring")

        for upload in self.uploads:
            if upload.status not in active_statuses or upload.user != user:
                continue

            already_downloading = True
            break

        if not self.allow_new_uploads() or already_downloading:
            transfer = Transfer(user=user, filename=filename, path=os.path.dirname(real_path),
                                status="Queued", size=self._get_file_size(real_path))
            self._append_upload(user, filename, transfer)
            self._update_upload(transfer)

            return slskmessages.TransferResponse(allowed=False, reason="Queued", token=token)

        # All checks passed, starting a new upload.
        size = self._get_file_size(real_path)
        transfer = Transfer(user=user, filename=filename, path=os.path.dirname(real_path),
                            status="Getting status", token=token, size=size)

        self.upload_requests[transfer] = time.time()
        self._append_upload(user, filename, transfer)
        self._update_upload(transfer)

        return slskmessages.TransferResponse(allowed=True, token=token, filesize=size)

    def _transfer_response(self, msg):
        """ Peer code: 41 """
        """ Received a response to the file request from the peer """

        username = msg.init.target_user
        token = msg.token
        reason = msg.reason

        log.add_transfer(("Received response for upload with token: %(token)s, allowed: %(allowed)s, "
                          "reason: %(reason)s, file size: %(size)s"), {
            "token": token,
            "allowed": msg.allowed,
            "reason": reason,
            "size": msg.filesize
        })

        if reason is not None:
            if reason in ("Queued", "Getting status", "Transferring", "Paused", "Filtered", "User logged off"):
                # Don't allow internal statuses as reason
                reason = "Cancelled"

            for upload in self.uploads:
                if upload.token != token or upload.user != username:
                    continue

                if upload.sock is not None:
                    log.add_transfer("Upload with token %s already has an existing file connection", token)
                    return

                self._abort_upload(upload, abort_reason=reason)

                if reason in ("Complete", "Finished"):
                    # A complete download of this file already exists on the user's end
                    self._upload_finished(upload)

                elif reason in ("Cancelled", "Disallowed extension"):
                    self._auto_clear_upload(upload)

                self.check_upload_queue()
                return

            return

        for upload in self.uploads:
            if upload.token != token or upload.user != username:
                continue

            if upload.sock is not None:
                log.add_transfer("Upload with token %s already has an existing file connection", token)
                return

            core.send_message_to_peer(upload.user, slskmessages.FileUploadInit(None, token=token))
            self.check_upload_queue()
            return

        log.add_transfer("Received unknown upload response: %s", msg)

    def _upload_file_error(self, username, token, error):
        """ Networking thread encountered a local file error for upload """

        for upload in self.uploads:
            if upload.token != token or upload.user != username:
                continue

            self._abort_upload(upload, abort_reason="Local file error")

            log.add(_("Upload I/O error: %s"), error)
            self.check_upload_queue()
            return

    def _file_upload_init(self, msg):
        """ We are requesting to start uploading a file to a peer """

        username = msg.init.target_user
        token = msg.token

        for upload in self.uploads:
            if upload.token != token or upload.user != username:
                continue

            filename = upload.filename

            log.add_transfer("Initializing upload with token %(token)s for file %(filename)s to user %(user)s", {
                "token": token,
                "filename": filename,
                "user": username
            })

            if upload.sock is not None:
                log.add_transfer("Upload already has an existing file connection, ignoring init message")
                core.queue.append(slskmessages.CloseConnection(msg.init.sock))
                return

            need_update = True
            upload.sock = msg.init.sock

            real_path = core.shares.virtual2real(filename)

            if not core.shares.file_is_shared(username, filename, real_path):
                self._abort_upload(upload, abort_reason="File not shared.")
                self.check_upload_queue()
                return

            try:
                # Open File
                file_handle = open(encode_path(real_path), "rb")  # pylint: disable=consider-using-with

            except OSError as error:
                log.add(_("Upload I/O error: %s"), error)
                self._abort_upload(upload, abort_reason="Local file error")
                self.check_upload_queue()

            else:
                upload.file = file_handle
                upload.queue_position = 0
                upload.last_update = time.time()
                upload.start_time = upload.last_update - upload.time_elapsed

                core.statistics.append_stat_value("started_uploads", 1)
                core.pluginhandler.upload_started_notification(username, filename, real_path)

                log.add_upload(
                    _("Upload started: user %(user)s, IP address %(ip)s, file %(file)s"), {
                        "user": username,
                        "ip": core.user_addresses.get(username),
                        "file": filename
                    }
                )

                if upload.size > 0:
                    upload.status = "Transferring"
                    core.queue.append(slskmessages.UploadFile(
                        init=msg.init, token=token, file=file_handle, size=upload.size
                    ))

                else:
                    self._upload_finished(upload, file_handle=file_handle)
                    need_update = False

            events.emit("upload-notification")

            if need_update:
                self._update_upload(upload)

            return

        log.add_transfer("Unknown file upload init message with token %s", token)
        core.queue.append(slskmessages.CloseConnection(msg.init.sock))

    def _file_upload_progress(self, username, token, offset, bytes_sent):
        """ A file upload is in progress """

        for upload in self.uploads:
            if upload.token != token or upload.user != username:
                continue

            if upload in self.upload_requests:
                del self.upload_requests[upload]

            current_time = time.time()
            size = upload.size

            if not upload.last_byte_offset:
                upload.last_byte_offset = offset

            upload.status = "Transferring"
            upload.time_elapsed = current_time - upload.start_time
            upload.current_byte_offset = current_byte_offset = (offset + bytes_sent)
            byte_difference = current_byte_offset - upload.last_byte_offset

            if byte_difference:
                core.statistics.append_stat_value("uploaded_size", byte_difference)

                if size > current_byte_offset or upload.speed is None:
                    upload.speed = int(max(0, byte_difference // max(1, current_time - upload.last_update)))
                    upload.time_left = (size - current_byte_offset) // upload.speed if upload.speed else 0
                else:
                    upload.time_left = 0

            upload.last_byte_offset = current_byte_offset
            upload.last_update = current_time

            self._update_upload(upload)
            return

    def _upload_connection_closed(self, username, token, timed_out):
        """ A file upload connection has closed for any reason """

        # We need a copy due to upload auto-clearing modifying the deque during iteration
        for upload in self.uploads.copy():
            if upload.token != token or upload.user != username:
                continue

            if not timed_out and upload.current_byte_offset is not None and upload.current_byte_offset >= upload.size:
                # We finish the upload here in case the downloading peer has a slow/limited download
                # speed and finishes later than us

                if upload.speed is not None:
                    # Inform the server about the last upload speed for this transfer
                    log.add_transfer("Sending upload speed %s to the server", human_speed(upload.speed))
                    core.queue.append(slskmessages.SendUploadSpeed(upload.speed))

                self._upload_finished(upload, file_handle=upload.file)
                return

            if upload.status == "Finished":
                return

            status = None

            if core.user_statuses.get(upload.user) == slskmessages.UserStatus.OFFLINE:
                status = "User logged off"
            else:
                status = "Cancelled"

                # Transfer ended abruptly. Tell the peer to re-queue the file. If the transfer was
                # intentionally cancelled, the peer should ignore this message.
                core.send_message_to_peer(upload.user, slskmessages.UploadFailed(file=upload.filename))

            if not self._auto_clear_upload(upload):
                self._abort_upload(upload, abort_reason=status)

            self.check_upload_queue()
            return

    def _place_in_queue_request(self, msg):
        """ Peer code: 51 """

        user = msg.init.target_user
        filename = msg.file
        privileged_user = self._is_privileged(user)
        queue_position = 0
        transfer = None

        if config.sections["transfers"]["fifoqueue"]:
            for upload in reversed(self.uploads):
                # Ignore non-queued files
                if upload.status != "Queued":
                    continue

                if not privileged_user or self._is_privileged(upload.user):
                    queue_position += 1

                # Stop counting on the matching file
                if upload.filename == filename and upload.user == user:
                    transfer = upload
                    break

        else:
            num_queued_users = len(self.user_update_counters)

            for upload in reversed(self.uploads):
                if upload.user != user:
                    continue

                # Ignore non-queued files
                if upload.status != "Queued":
                    continue

                queue_position += num_queued_users

                # Stop counting on the matching file
                if upload.filename == filename:
                    transfer = upload
                    break

        if queue_position > 0:
            core.queue.append(slskmessages.PlaceInQueueResponse(init=msg.init, filename=filename, place=queue_position))

        if transfer is None:
            return

        # Update queue position in our list of uploads
        transfer.queue_position = queue_position
        self._update_upload(transfer, update_parent=False)

    """ Upload Transfer Actions """

    def push_file(self, user, filename, size, path="", transfer=None, locally_queued=False):

        real_path = core.shares.virtual2real(filename)
        size_attempt = self._get_file_size(real_path)

        if path:
            path = os.path.normpath(path)

        if size_attempt > 0:
            size = size_attempt

        if transfer is None:
            if not path:
                path = os.path.dirname(real_path)

            transfer = Transfer(user=user, filename=filename, path=path, status="Queued", size=size)
            self._append_upload(user, filename, transfer)
        else:
            transfer.filename = filename
            transfer.size = size
            transfer.status = "Queued"
            transfer.token = None

        log.add_transfer("Initializing upload request for file %(file)s to user %(user)s", {
            "file": filename,
            "user": user
        })

        core.watch_user(user)

        if slskmessages.UserStatus.OFFLINE in (core.user_status, core.user_statuses.get(user)):
            # Either we are offline or the user we want to upload to is
            transfer.status = "User logged off"

            if not self._auto_clear_upload(transfer):
                self._update_upload(transfer)
            return

        if not locally_queued:
            self.token = slskmessages.increment_token(core.transfers.token)
            transfer.token = self.token
            transfer.status = "Getting status"
            self.upload_requests[transfer] = time.time()

            log.add_transfer("Requesting to upload file %(filename)s with token %(token)s to user %(user)s", {
                "filename": filename,
                "token": transfer.token,
                "user": user
            })

            core.send_message_to_peer(
                user, slskmessages.TransferRequest(
                    direction=slskmessages.TransferDirection.UPLOAD, token=transfer.token, file=filename,
                    filesize=size, realfile=real_path))

        self._update_upload(transfer)

    def _append_upload(self, user, filename, transferobj):

        previously_queued = False
        old_index = 0

        if self._is_privileged(user):
            transferobj.modifier = "privileged" if user in self.privileged_users else "prioritized"

        for upload in self.uploads:
            if upload.filename == filename and upload.user == user:
                if upload.status == "Queued":
                    # This upload was queued previously
                    # Use the previous queue position
                    transferobj.queue_position = upload.queue_position
                    previously_queued = True

                if upload.status != "Finished":
                    transferobj.current_byte_offset = upload.current_byte_offset
                    transferobj.time_elapsed = upload.time_elapsed
                    transferobj.time_left = upload.time_left
                    transferobj.speed = upload.speed

                if upload in self.upload_requests:
                    del self.upload_requests[upload]

                self.clear_upload(upload)
                break

            old_index += 1

        if previously_queued:
            self.uploads.insert(old_index, transferobj)
            return

        self.uploads.appendleft(transferobj)

    def get_total_uploads_allowed(self):

        if config.sections["transfers"]["useupslots"]:
            maxupslots = config.sections["transfers"]["uploadslots"]

            if maxupslots <= 0:
                maxupslots = 1

            return maxupslots

        lstlen = sum(1 for upload in self.uploads if upload.sock is not None)

        if self.allow_new_uploads():
            return lstlen + 1

        return lstlen or 1

    def get_upload_queue_size(self, username=None):

        if self._is_privileged(username):
            queue_size = 0

            for upload in self.uploads:
                if upload.status == "Queued" and self._is_privileged(upload.user):
                    queue_size += 1

            return queue_size

        return sum(1 for upload in self.uploads if upload.status == "Queued")

    def get_downloading_users(self):

        statuses = ("Queued", "Getting status", "Transferring")
        users = set()

        for upload in self.uploads:
            if upload.status in statuses:
                users.add(upload.user)

        return users

    def _upload_finished(self, transfer, file_handle=None):

        core.transfers.close_file(file_handle, transfer)

        if transfer in self.upload_requests:
            del self.upload_requests[transfer]

        transfer.status = "Finished"
        transfer.current_byte_offset = transfer.size
        transfer.sock = None
        transfer.token = None

        log.add_upload(
            _("Upload finished: user %(user)s, IP address %(ip)s, file %(file)s"), {
                "user": transfer.user,
                "ip": core.user_addresses.get(transfer.user),
                "file": transfer.filename
            }
        )

        core.statistics.append_stat_value("completed_uploads", 1)

        # Autoclear this upload
        if not self._auto_clear_upload(transfer):
            self._update_upload(transfer)

        real_path = core.shares.virtual2real(transfer.filename)
        core.pluginhandler.upload_finished_notification(transfer.user, transfer.filename, real_path)

        self.check_upload_queue()

    def _auto_clear_upload(self, upload):

        if config.sections["transfers"]["autoclear_uploads"]:
            self._update_user_counter(upload.user)
            self.clear_upload(upload)
            return True

        return False

    def _update_upload(self, transfer, update_parent=True):

        user = transfer.user
        status = transfer.status

        events.emit("update-upload", transfer, update_parent)

        if status == "Queued" and user in self.user_update_counters:
            # Don't update existing user counter for queued uploads
            # We don't want to push the user back in the queue if they enqueued new files
            return

        if status == "Transferring":
            # Avoid unnecessary updates while transferring
            return

        self._update_user_counter(user)

    def check_upload_timeouts(self, timeout):

        if not timeout or not self.upload_requests:
            return

        abort_reason = "Connection timeout"
        current_time = time.time()
        need_update = False

        for transfer, start_time in self.upload_requests.copy().items():
            if (current_time - start_time) >= timeout:
                core.transfers.transfer_timeout(transfer)
                self._abort_upload(transfer, abort_reason=abort_reason, update_parent=False)  # TODO: test this change

                need_update = True

        if need_update:
            events.emit("update-uploads")  # TODO: test this change, consider only update specific user rows
            # self.check_upload_queue()  # TODO consider

    def _check_queue_upload_allowed(self, user, addr, filename, real_path, msg):

        # Is user allowed to download?
        ip_address, _port = addr
        checkuser, reason = core.network_filter.check_user(user, ip_address)

        if not checkuser:
            return False, reason

        if core.shares.rescanning:
            core.shares.pending_network_msgs.append(msg)
            return False, None

        # Is that file already in the queue?
        if self._file_is_upload_queued(user, filename):
            return False, "Queued"

        # Has user hit queue limit?
        enable_limits = True

        if config.sections["transfers"]["friendsnolimits"]:
            if user in core.userlist.buddies:
                enable_limits = False

        if enable_limits:
            limit_reached, reason = self._queue_limit_reached(user)

            if limit_reached:
                return False, reason

        # Do we actually share that file with the world?
        if (not core.shares.file_is_shared(user, filename, real_path)
                or not self._file_is_readable(filename, real_path)):
            return False, "File not shared."

        return True, None

    def _get_upload_candidate(self):
        """ Retrieve a suitable queued transfer for uploading.
        Round Robin: Get the first queued item from the oldest user
        FIFO: Get the first queued item in the list """

        round_robin_queue = not config.sections["transfers"]["fifoqueue"]
        active_statuses = ("Getting status", "Transferring")
        privileged_queue = False

        first_queued_transfers = {}
        queued_users = {}
        uploading_users = set()

        for upload in reversed(self.uploads):
            if upload.status == "Queued":
                user = upload.user

                if user not in first_queued_transfers and user not in uploading_users:
                    first_queued_transfers[user] = upload

                if user in queued_users:
                    continue

                privileged = self._is_privileged(user)
                queued_users[user] = privileged

            elif upload.status in active_statuses:
                # We're currently uploading a file to the user
                user = upload.user

                if user in uploading_users:
                    continue

                uploading_users.add(user)

                if user in first_queued_transfers:
                    del first_queued_transfers[user]

        oldest_time = None
        target_user = None

        for user, privileged in queued_users.items():
            if privileged and user not in uploading_users:
                privileged_queue = True
                break

        if not round_robin_queue:
            # skip the looping below (except the cleanup) and get the first
            # user of the highest priority we saw above
            for user in first_queued_transfers:
                if privileged_queue and not queued_users[user]:
                    continue

                target_user = user
                break

        for user, update_time in self.user_update_counters.copy().items():
            if user not in queued_users:
                del self.user_update_counters[user]
                continue

            if not round_robin_queue or user in uploading_users:
                continue

            if privileged_queue and not queued_users[user]:
                continue

            if not oldest_time:
                oldest_time = update_time + 1

            if update_time < oldest_time:
                target_user = user
                oldest_time = update_time

        if not target_user:
            return None

        return first_queued_transfers[target_user]

    def check_upload_queue(self):
        """ Find next file to upload """

        if not self.uploads:
            # No uploads exist
            return

        if not self.allow_new_uploads():
            return

        upload_candidate = self._get_upload_candidate()

        if upload_candidate is None:
            return

        user = upload_candidate.user

        log.add_transfer(
            "Attempting to upload file %(file)s to user %(user)s", {
                "file": upload_candidate.filename,
                "user": user
            }
        )

        self.push_file(
            user=user, filename=upload_candidate.filename, size=upload_candidate.size, transfer=upload_candidate
        )

    def _update_user_counter(self, user):
        """ Called when an upload associated with a user has changed. The user update counter
        is used by the Round Robin queue system to determine which user has waited the longest
        since their last download. """

        self.user_update_counter += 1
        self.user_update_counters[user] = self.user_update_counter

    def ban_users(self, users, ban_message=None):
        """ Ban a user, cancel all the user's uploads, send a 'Banned'
        message via the transfers, and clear the transfers from the
        uploads list. """

        if not ban_message and config.sections["transfers"]["usecustomban"]:
            ban_message = config.sections["transfers"]["customban"]

        if ban_message:
            banmsg = f"Banned ({ban_message})"
        else:
            banmsg = "Banned"

        for upload in self.uploads.copy():
            if upload.user not in users:
                continue

            self.clear_upload(upload, denied_message=banmsg)

        for user in users:
            core.network_filter.ban_user(user)

        self.check_upload_queue()

    def _retry_upload(self, transfer):

        active_statuses = ["Getting status", "Transferring"]

        if transfer.status in active_statuses + ["Finished"]:
            # Don't retry active or finished uploads
            return

        user = transfer.user

        for upload in self.uploads:
            if upload.user != user:
                continue

            if upload.status in active_statuses:
                # User already has an active upload, queue the retry attempt
                if transfer.status != "Queued":
                    transfer.status = "Queued"
                    self._update_upload(transfer)  # , update_parent=False)  # TODO
                return

        self.push_file(user, transfer.filename, transfer.size, transfer=transfer)

    def retry_uploads(self, uploads):
        for upload in uploads:
            self._retry_upload(upload)

    def retry_failed_uploads(self):

        for upload in reversed(self.uploads):
            if upload.status == "Connection timeout":
                upload.status = "Queued"
                self._update_upload(upload)  # , update_parent=False)  # TODO

    def _abort_upload(self, upload, denied_message=None, abort_reason="Cancelled", update_parent=True):

        log.add_transfer(('Aborting upload, user "%(user)s", filename "%(filename)s", token "%(token)s", '
                          'status "%(status)s"'), {
            "user": upload.user,
            "filename": upload.filename,
            "token": upload.token,
            "status": upload.status
        })

        upload.token = None
        upload.queue_position = 0

        if upload in self.upload_requests:
            del self.upload_requests[upload]

        if upload.sock is not None:
            core.queue.append(slskmessages.CloseConnection(upload.sock))
            upload.sock = None

        if upload.file is not None:
            core.transfers.close_file(upload.file, upload)

            log.add_upload(
                _("Upload aborted, user %(user)s file %(file)s"), {
                    "user": upload.user,
                    "file": upload.filename
                }
            )

        elif denied_message and upload.status == "Queued":
            core.send_message_to_peer(
                upload.user, slskmessages.UploadDenied(file=upload.filename, reason=denied_message))

        if abort_reason:
            upload.status = abort_reason

        events.emit("abort-upload", upload, abort_reason, update_parent)

    def abort_uploads(self, uploads, denied_message=None, abort_reason="Cancelled"):

        for upload in uploads:
            if upload.status not in (abort_reason, "Finished"):
                self._abort_upload(
                    upload, denied_message=denied_message, abort_reason=abort_reason, update_parent=False)

        events.emit("abort-uploads", uploads, abort_reason)

    def clear_upload(self, upload, denied_message=None, update_parent=True):

        self._abort_upload(upload, denied_message=denied_message, abort_reason=None)
        self.uploads.remove(upload)

        events.emit("clear-upload", upload, update_parent)

    def clear_uploads(self, uploads=None, statuses=None):

        if uploads is None:
            # Clear all uploads
            uploads = self.uploads

        for upload in uploads.copy():
            if statuses and upload.status not in statuses:
                continue

            self.clear_upload(upload, update_parent=False)

        events.emit("clear-uploads", uploads, statuses)

    """ Saving """

    def get_uploads(self):
        """ Get a list of finished uploads """
        return [
            [upload.user, upload.filename, upload.path, upload.status, upload.size, upload.current_byte_offset,
             upload.file_attributes]
            for upload in reversed(self.uploads) if upload.status == "Finished"
        ]

    def save_uploads_callback(self, filename):
        json.dump(self.get_uploads(), filename, ensure_ascii=False)
