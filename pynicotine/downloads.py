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

from collections import defaultdict
from locale import strxfrm

from pynicotine import slskmessages
from pynicotine.config import config
from pynicotine.core import core
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.transfers import Transfer
from pynicotine.utils import execute_command
from pynicotine.utils import clean_file
from pynicotine.utils import clean_path
from pynicotine.utils import encode_path
from pynicotine.utils import truncate_string_byte


class Downloads():
    """ This is the downloads manager """

    def __init__(self):

        self.downloads = None
        self.download_requests = {}
        self.requested_folders = defaultdict(dict)

        self._download_queue_timer_id = None
        self._retry_download_limits_timer_id = None

        for event_name, callback in (
            ("download-connection-closed", self._download_connection_closed),
            ("download-file-error", self._download_file_error),
            ("file-download-init", self._file_download_init),
            ("file-download-progress", self._file_download_progress),
            ("place-in-queue-response", self._place_in_queue_response),
            ("quit", self._quit),
            ("server-login", self._server_login),
            ("server-disconnect", self._server_disconnect),
            ("start", self._start),
            ("upload-denied", self._upload_denied),
            ("upload-failed", self._upload_failed),
            ("user-status", self._user_status)
        ):
            events.connect(event_name, callback)

    def init_downloads(self, transfer_list):
        self.downloads = transfer_list

    def _start(self):

        self.update_download_filters()
        self.update_download_limits()

    def _quit(self):
        self.downloads.clear()

    def _server_login(self, msg):

        if not msg.success:
            return

        self.requested_folders.clear()
        self.update_download_limits()
        self._watch_stored_downloads()

        # Every 3 minutes: Request queue position of queued downloads and retry failed downloads
        self._download_queue_timer_id = events.schedule(
            delay=180,
            callback=self.check_download_queue,
            repeat=True
        )

        # Every 12 minutes: Re-queue limited downloads
        self._retry_download_limits_timer_id = events.schedule(
            delay=720,
            callback=self.retry_download_limits,
            repeat=True
        )

    def _server_disconnect(self, _msg):

        for timer_id in (self._download_queue_timer_id, self._retry_download_limits_timer_id):
            events.cancel_scheduled(timer_id)

        need_update = False

        for download in self.downloads:
            if download.status not in ("Finished", "Filtered", "Paused"):
                download.status = "User logged off"
                self._abort_download(download, abort_reason=None)
                need_update = True

        if need_update:
            events.emit("update-downloads")

        self.requested_folders.clear()

    """ Load Transfers """

    def get_download_queue_file_name(self):

        data_dir = config.data_dir
        downloads_file_json = os.path.join(data_dir, "downloads.json")
        downloads_file_1_4_2 = os.path.join(data_dir, "config.transfers.pickle")
        downloads_file_1_4_1 = os.path.join(data_dir, "transfers.pickle")

        if os.path.exists(encode_path(downloads_file_json)):
            # New file format
            return downloads_file_json

        if os.path.exists(encode_path(downloads_file_1_4_2)):
            # Nicotine+ 1.4.2+
            return downloads_file_1_4_2

        if os.path.exists(encode_path(downloads_file_1_4_1)):
            # Nicotine <=1.4.1
            return downloads_file_1_4_1

        # Fall back to new file format
        return downloads_file_json

    def _watch_stored_downloads(self):
        """ When logging in, we request to watch the status of our downloads """

        users = set()

        for download in self.downloads:
            if download.status in ("Filtered", "Finished"):
                continue

            users.add(download.user)

        for user in users:
            core.watch_user(user)

    """ Limits """

    def update_download_limits(self):

        events.emit("update-download-limits")

        if core.user_status == slskmessages.UserStatus.OFFLINE:
            return

        use_speed_limit = config.sections["transfers"]["use_download_speed_limit"]

        if use_speed_limit == "primary":
            speed_limit = config.sections["transfers"]["downloadlimit"]

        elif use_speed_limit == "alternative":
            speed_limit = config.sections["transfers"]["downloadlimitalt"]

        else:
            speed_limit = 0

        core.queue.append(slskmessages.SetDownloadLimit(speed_limit))

    """ Events """

    def _user_status(self, msg):
        """ Server code: 7 """
        """ We get a status of a user and if he's online, we request a file from him """

        update = False
        username = msg.user
        user_offline = (msg.status == slskmessages.UserStatus.OFFLINE)
        download_statuses = ("Queued", "Getting status", "Too many files", "Too many megabytes", "Pending shutdown.",
                             "User logged off", "Connection timeout", "Remote file error", "Cancelled")

        for download in reversed(self.downloads.copy()):
            if (download.user == username
                    and (download.status in download_statuses or download.status.startswith("User limit of"))):
                if user_offline:
                    download.status = "User logged off"
                    self._abort_download(download, abort_reason=None)
                    update = True

                elif download.status == "User logged off":
                    self.get_file(username, download.filename, transfer=download, ui_callback=False)
                    update = True

        if update:
            events.emit("update-downloads")

    def cant_connect_queue_file(self, username, filename, is_offline):
        """ We can't connect to the user, either way (QueueUpload). """

        for download in self.downloads:
            if download.filename != filename or download.user != username:
                continue

            log.add_transfer("Download attempt for file %(filename)s from user %(user)s timed out", {
                "filename": filename,
                "user": username
            })

            self._abort_download(download, abort_reason="User logged off" if is_offline else "Connection timeout")
            core.watch_user(username)
            break

    def _folder_contents_response(self, msg, check_num_files=True):
        """ Peer code: 37 """
        """ When we got a contents of a folder, get all the files in it, but
        skip the files in subfolders """

        username = msg.init.target_user
        file_list = msg.list

        log.add_transfer("Received response for folder content request from user %s", username)

        for i in file_list:
            for directory in file_list[i]:
                if os.path.commonprefix([i, directory]) != directory:
                    continue

                files = file_list[i][directory][:]
                num_files = len(files)

                if check_num_files and num_files > 100:
                    events.emit("download-large-folder", username, directory, num_files, msg)
                    return

                destination = self.get_folder_destination(username, directory)

                if num_files > 1:
                    files.sort(key=lambda x: strxfrm(x[1]))

                log.add_transfer(("Attempting to download files in folder %(folder)s for user %(user)s. "
                                  "Destination path: %(destination)s"), {
                    "folder": directory,
                    "user": username,
                    "destination": destination
                })

                for _code, filename, file_size, _ext, file_attributes, *_unused in files:
                    virtualpath = directory.rstrip("\\") + "\\" + filename

                    self.get_file(
                        username, virtualpath, path=destination, size=file_size, file_attributes=file_attributes)

    def _can_upload(self, user):

        transfers = config.sections["transfers"]

        if transfers["remotedownloads"]:

            if transfers["uploadallowed"] == 0:
                # No One can sent files to you
                return False

            if transfers["uploadallowed"] == 1:
                # Everyone can sent files to you
                return True

            if transfers["uploadallowed"] == 2 and user in core.userlist.buddies:
                # Users in userlist
                return True

            if transfers["uploadallowed"] == 3:
                # Trusted buddies
                user_data = core.userlist.buddies.get(user)

                if user_data and user_data.is_trusted:
                    return True

        return False

    def transfer_request(self, msg):

        user = msg.init.target_user
        filename = msg.file
        size = msg.filesize
        token = msg.token

        log.add_transfer("Received download request with token %(token)s for file %(filename)s from user %(user)s", {
            "token": token,
            "filename": filename,
            "user": user
        })

        cancel_reason = "Cancelled"
        accepted = True

        for download in self.downloads:
            if download.filename != filename or download.user != user:
                continue

            status = download.status

            if status == "Finished":
                # SoulseekQt sends "Complete" as the reason for rejecting the download if it exists
                cancel_reason = "Complete"
                accepted = False
                break

            if status in ("Paused", "Filtered"):
                accepted = False
                break

            # Remote peer is signaling a transfer is ready, attempting to download it

            # If the file is larger than 2GB, the SoulseekQt client seems to
            # send a malformed file size (0 bytes) in the TransferRequest response.
            # In that case, we rely on the cached, correct file size we received when
            # we initially added the download.

            if size > 0:
                if download.size != size:
                    # The remote user's file contents have changed since we queued the download
                    download.size_changed = True

                download.size = size

            download.token = token
            download.status = "Getting status"
            self.download_requests[download] = time.time()

            self._update_download(download)
            return slskmessages.TransferResponse(allowed=True, token=token)

        # Check if download exists in our default download folder
        if self._get_complete_download_file_path(user, filename, "", size):
            cancel_reason = "Complete"
            accepted = False

        # If this file is not in your download queue, then it must be
        # a remotely initiated download and someone is manually uploading to you
        if accepted and self._can_upload(user):
            path = ""
            if config.sections["transfers"]["uploadsinsubdirs"]:
                parentdir = filename.replace("/", "\\").split("\\")[-2]
                path = os.path.join(os.path.normpath(config.sections["transfers"]["uploaddir"]), user, parentdir)

            transfer = Transfer(user=user, filename=filename, path=path, status="Queued",
                                size=size, token=token)
            self.downloads.appendleft(transfer)
            self._update_download(transfer)
            core.watch_user(user)

            return slskmessages.TransferResponse(allowed=True, token=token)

        log.add_transfer("Denied file request: User %(user)s, %(msg)s", {
            "user": user,
            "msg": msg
        })

        return slskmessages.TransferResponse(allowed=False, reason=cancel_reason, token=token)

    def _download_file_error(self, username, token, error):
        """ Networking thread encountered a local file error for download """

        for download in self.downloads:
            if download.token != token or download.user != username:
                continue

            self._abort_download(download, abort_reason="Local file error")
            log.add(_("Download I/O error: %s"), error)
            return

    def _file_download_init(self, msg):
        """ A peer is requesting to start uploading a file to us """

        username = msg.init.target_user
        token = msg.token

        for download in self.downloads:
            if download.token != token or download.user != username:
                continue

            filename = download.filename

            log.add_transfer(("Received file download init with token %(token)s for file %(filename)s "
                              "from user %(user)s"), {
                "token": token,
                "filename": filename,
                "user": username
            })

            if download.sock is not None:
                log.add_transfer("Download already has an existing file connection, ignoring init message")
                core.queue.append(slskmessages.CloseConnection(msg.init.sock))
                return

            incomplete_folder_path = os.path.normpath(config.sections["transfers"]["incompletedir"])
            need_update = True
            download.sock = msg.init.sock

            try:
                incomplete_folder_path_encoded = encode_path(incomplete_folder_path)

                if not os.path.isdir(incomplete_folder_path_encoded):
                    os.makedirs(incomplete_folder_path_encoded)

                incomplete_file_path = self._get_incomplete_download_file_path(username, filename)
                file_handle = open(encode_path(incomplete_file_path), "ab+")  # pylint: disable=consider-using-with

                try:
                    import fcntl
                    try:
                        fcntl.lockf(file_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError as error:
                        log.add(_("Can't get an exclusive lock on file - I/O error: %s"), error)
                except ImportError:
                    pass

                if download.size_changed:
                    # Remote user sent a different file size than we originally requested,
                    # wipe any existing data in the incomplete file to avoid corruption
                    file_handle.truncate(0)

                # Seek to the end of the file for resuming the download
                offset = file_handle.seek(0, os.SEEK_END)

            except OSError as error:
                log.add(_("Cannot save file in %(folder_path)s: %(error)s"), {
                    "folder_path": incomplete_folder_path,
                    "error": error
                })
                self._abort_download(download, abort_reason="Download folder error")
                core.notifications.show_download_notification(
                    str(error), title=_("Download Folder Error"), high_priority=True)
                need_update = False

            else:
                download.file = file_handle
                download.last_byte_offset = offset
                download.queue_position = 0
                download.last_update = time.time()
                download.start_time = download.last_update - download.time_elapsed

                core.statistics.append_stat_value("started_downloads", 1)
                core.pluginhandler.download_started_notification(username, filename, incomplete_file_path)

                log.add_download(
                    _("Download started: user %(user)s, file %(file)s"), {
                        "user": username,
                        "file": file_handle.name.decode("utf-8", "replace")
                    }
                )

                if download.size > offset:
                    download.status = "Transferring"
                    core.queue.append(slskmessages.DownloadFile(
                        init=msg.init, token=token, file=file_handle, leftbytes=(download.size - offset)
                    ))
                    core.queue.append(slskmessages.FileOffset(init=msg.init, offset=offset))

                else:
                    self._download_finished(download, file_handle=file_handle)
                    need_update = False

            events.emit("download-notification")

            if need_update:
                self._update_download(download)

            return

        # Support legacy transfer system (clients: old Nicotine+ versions, slskd)
        # The user who requested the download initiates the file upload connection
        # in this case, but we always assume an incoming file init message is
        # FileDownloadInit

        log.add_transfer(("Received unknown file download init message with token %s, checking if peer "
                          "requested us to upload a file instead"), token)
        events.emit("file-upload-init", msg)

    def _upload_denied(self, msg):
        """ Peer code: 50 """

        user = msg.init.target_user
        filename = msg.file
        reason = msg.reason

        if reason in ("Getting status", "Transferring", "Paused", "Filtered", "User logged off", "Finished"):
            # Don't allow internal statuses as reason
            reason = "Cancelled"

        for download in self.downloads:
            if download.filename != filename or download.user != user:
                continue

            if download.status in ("Finished", "Paused"):
                # SoulseekQt also sends this message for finished downloads when unsharing files, ignore
                continue

            if reason in ("File not shared.", "File not shared", "Remote file error") and not download.legacy_attempt:
                # The peer is possibly using an old client that doesn't support Unicode
                # (Soulseek NS). Attempt to request file name encoded as latin-1 once.

                log.add_transfer("User %(user)s responded with reason '%(reason)s' for download request %(filename)s. "
                                 "Attempting to request file as latin-1.", {
                                     "user": user,
                                     "reason": reason,
                                     "filename": filename
                                 })

                self._abort_download(download, abort_reason=None)
                download.legacy_attempt = True
                self.get_file(user, filename, transfer=download)
                break

            if download.status == "Transferring":
                self._abort_download(download, abort_reason=None)

            download.status = reason
            self._update_download(download)

            log.add_transfer("Download request denied by user %(user)s for file %(filename)s. Reason: %(reason)s", {
                "user": user,
                "filename": filename,
                "reason": msg.reason
            })
            return

    def _upload_failed(self, msg):
        """ Peer code: 46 """

        user = msg.init.target_user
        filename = msg.file

        for download in self.downloads:
            if download.filename != filename or download.user != user:
                continue

            if download.status in ("Finished", "Paused", "Download folder error", "Local file error",
                                   "User logged off"):
                # Check if there are more transfers with the same virtual path
                continue

            should_retry = not download.legacy_attempt

            if should_retry:
                # Attempt to request file name encoded as latin-1 once

                self._abort_download(download, abort_reason=None)
                download.legacy_attempt = True
                self.get_file(user, filename, transfer=download)
                break

            # Already failed once previously, give up
            self._abort_download(download, abort_reason="Remote file error")

            log.add_transfer("Upload attempt by user %(user)s for file %(filename)s failed. Reason: %(reason)s", {
                "filename": filename,
                "user": user,
                "reason": download.status
            })
            return

    def _file_download_progress(self, username, token, bytes_left):
        """ A file download is in progress """

        for download in self.downloads:
            if download.token != token or download.user != username:
                continue

            if download in self.download_requests:
                del self.download_requests[download]

            current_time = time.time()
            size = download.size

            download.status = "Transferring"
            download.time_elapsed = current_time - download.start_time
            download.current_byte_offset = current_byte_offset = (size - bytes_left)
            byte_difference = current_byte_offset - download.last_byte_offset

            if byte_difference:
                core.statistics.append_stat_value("downloaded_size", byte_difference)

                if size > current_byte_offset or download.speed is None:
                    download.speed = int(max(0, byte_difference // max(1, current_time - download.last_update)))
                    download.time_left = (size - current_byte_offset) // download.speed if download.speed else 0
                else:
                    download.time_left = 0

            download.last_byte_offset = current_byte_offset
            download.last_update = current_time

            self._update_download(download)
            return

    def _download_connection_closed(self, username, token):
        """ A file download connection has closed for any reason """

        for download in self.downloads:
            if download.token != token or download.user != username:
                continue

            if download.current_byte_offset is not None and download.current_byte_offset >= download.size:
                self._download_finished(download, file_handle=download.file)
                return

            status = None

            if download.status != "Finished":
                if core.user_statuses.get(download.user) == slskmessages.UserStatus.OFFLINE:
                    status = "User logged off"
                else:
                    status = "Cancelled"

            self._abort_download(download, abort_reason=status)
            return

    def _place_in_queue_response(self, msg):
        """ Peer code: 44 """
        """ The peer tells us our place in queue for a particular transfer """

        username = msg.init.target_user
        filename = msg.filename

        for download in self.downloads:
            if download.filename == filename and download.status == "Queued" and download.user == username:
                download.queue_position = msg.place
                self._update_download(download, update_parent=False)
                return

    """ Download Transfer Actions """

    def get_folder(self, user, folder):
        core.send_message_to_peer(user, slskmessages.FolderContentsRequest(directory=folder, token=1))

    def get_file(self, user, filename, path="", transfer=None, size=0, file_attributes=None,
                 bypass_filter=False, ui_callback=True):

        if path:
            path = clean_path(path)
        else:
            path = self._get_default_download_folder(user)

        if transfer is None:
            for download in self.downloads:
                if download.filename == filename and download.path == path and download.user == user:
                    if download.status == "Finished":
                        # Duplicate finished download found, verify that it's still present on disk later
                        transfer = download
                        break

                    # Duplicate active/cancelled download found, stop here
                    return

            else:
                transfer = Transfer(
                    user=user, filename=filename, path=path,
                    status="Queued", size=size, file_attributes=file_attributes
                )
                self.downloads.appendleft(transfer)
        else:
            transfer.filename = filename
            transfer.status = "Queued"
            transfer.token = None

        core.watch_user(user)

        if not bypass_filter and config.sections["transfers"]["enablefilters"]:
            try:
                downloadregexp = re.compile(config.sections["transfers"]["downloadregexp"], flags=re.IGNORECASE)

                if downloadregexp.search(filename) is not None:
                    log.add_transfer("Filtering: %s", filename)

                    if self._auto_clear_download(transfer):
                        return

                    self._abort_download(transfer, abort_reason="Filtered")

            except re.error:
                pass

        if slskmessages.UserStatus.OFFLINE in (core.user_status, core.user_statuses.get(user)):
            # Either we are offline or the user we want to download from is
            transfer.status = "User logged off"

        elif transfer.status != "Filtered":
            download_path = self._get_complete_download_file_path(user, filename, transfer.path, size)

            if download_path:
                transfer.status = "Finished"
                transfer.size = transfer.current_byte_offset = size

                log.add_transfer("File %s is already downloaded", download_path)

            else:
                log.add_transfer("Adding file %(filename)s from user %(user)s to download queue", {
                    "filename": filename,
                    "user": user
                })
                core.send_message_to_peer(
                    user, slskmessages.QueueUpload(file=filename, legacy_client=transfer.legacy_attempt))

        if ui_callback:
            self._update_download(transfer)

    def get_folder_destination(self, user, folder, remove_prefix="", remove_destination=True):

        if not remove_prefix and "\\" in folder:
            remove_prefix = folder.rsplit("\\", 1)[0]

        # Get the last folders in folder path, excluding remove_prefix
        target_folders = folder.replace(remove_prefix, "").lstrip("\\").replace("\\", os.sep)

        # Check if a custom download location was specified
        if (user in self.requested_folders and folder in self.requested_folders[user]
                and self.requested_folders[user][folder]):
            download_location = self.requested_folders[user][folder]

            if remove_destination:
                del self.requested_folders[user][folder]
        else:
            download_location = self._get_default_download_folder(user)

        # Merge download path with target folder name
        return os.path.join(download_location, target_folders)

    def _get_default_download_folder(self, user):

        downloaddir = os.path.normpath(config.sections["transfers"]["downloaddir"])

        # Check if username subfolders should be created for downloads
        if config.sections["transfers"]["usernamesubfolders"]:
            try:
                downloaddir = os.path.join(downloaddir, clean_file(user))
                downloaddir_encoded = encode_path(downloaddir)

                if not os.path.isdir(downloaddir_encoded):
                    os.makedirs(downloaddir_encoded)

            except Exception as error:
                log.add(_("Unable to save download to username subfolder, falling back "
                          "to default download folder. Error: %s"), error)

        return downloaddir

    def _get_basename_byte_limit(self, folder_path):

        try:
            max_bytes = os.statvfs(encode_path(folder_path)).f_namemax

        except (AttributeError, OSError):
            max_bytes = 255

        return max_bytes

    def _get_download_basename(self, virtual_path, download_folder_path, avoid_conflict=False):
        """ Returns the download basename for a virtual file path """

        max_bytes = self._get_basename_byte_limit(download_folder_path)

        basename = clean_file(virtual_path.replace("/", "\\").split("\\")[-1])
        basename_no_extension, extension = os.path.splitext(basename)
        basename_limit = max_bytes - len(extension.encode("utf-8"))
        basename_no_extension = truncate_string_byte(basename_no_extension, max(0, basename_limit))

        if basename_limit < 0:
            extension = truncate_string_byte(extension, max_bytes)

        corrected_basename = basename_no_extension + extension

        if not avoid_conflict:
            return corrected_basename

        counter = 1

        while os.path.exists(encode_path(os.path.join(download_folder_path, corrected_basename))):
            corrected_basename = f"{basename_no_extension} ({counter}){extension}"
            counter += 1

        return corrected_basename

    def _get_complete_download_file_path(self, user, virtual_path, download_folder_path, size):
        """ Returns the download path of a complete download, if available """

        if not download_folder_path:
            download_folder_path = self._get_default_download_folder(user)

        basename = self._get_download_basename(virtual_path, download_folder_path)
        basename_no_extension, extension = os.path.splitext(basename)
        download_file_path = os.path.join(download_folder_path, basename)
        counter = 1

        while os.path.isfile(encode_path(download_file_path)):
            if os.stat(encode_path(download_file_path)).st_size == size:
                # Found a previous download with a matching file size
                return download_file_path

            basename = f"{basename_no_extension} ({counter}){extension}"
            download_file_path = os.path.join(download_folder_path, basename)
            counter += 1

        return None

    def _get_incomplete_download_file_path(self, username, virtual_path):
        """ Returns the path to store a download while it's still transferring """

        from hashlib import md5
        md5sum = md5()
        md5sum.update((virtual_path + username).encode("utf-8"))
        prefix = f"INCOMPLETE{md5sum.hexdigest()}"

        # Ensure file name length doesn't exceed file system limit
        incomplete_folder_path = os.path.normpath(config.sections["transfers"]["incompletedir"])
        max_bytes = self._get_basename_byte_limit(incomplete_folder_path)

        basename = clean_file(virtual_path.replace("/", "\\").split("\\")[-1])
        basename_no_extension, extension = os.path.splitext(basename)
        basename_limit = max_bytes - len(prefix) - len(extension.encode("utf-8"))
        basename_no_extension = truncate_string_byte(basename_no_extension, max(0, basename_limit))

        if basename_limit < 0:
            extension = truncate_string_byte(extension, max_bytes - len(prefix))

        return os.path.join(incomplete_folder_path, prefix + basename_no_extension + extension)

    def get_current_download_file_path(self, username, virtual_path, download_folder_path, size):
        """ Returns the current file path of a download """

        return (self._get_complete_download_file_path(username, virtual_path, download_folder_path, size)
                or self._get_incomplete_download_file_path(username, virtual_path))

    def _file_downloaded_actions(self, user, filepath):

        if config.sections["notifications"]["notification_popup_file"]:
            core.notifications.show_download_notification(
                _("%(file)s downloaded from %(user)s") % {
                    "user": user,
                    "file": os.path.basename(filepath)
                },
                title=_("File Downloaded")
            )

        if config.sections["transfers"]["afterfinish"]:
            try:
                execute_command(config.sections["transfers"]["afterfinish"], filepath)
                log.add(_("Executed: %s"), config.sections["transfers"]["afterfinish"])

            except Exception:
                log.add(_("Trouble executing '%s'"), config.sections["transfers"]["afterfinish"])

    def _folder_downloaded_actions(self, user, folderpath):

        # walk through downloads and break if any file in the same folder exists, else execute
        statuses = ("Finished", "Paused", "Filtered")

        for download in self.downloads:
            if download.path == folderpath and download.status not in statuses:
                return

        if not folderpath:
            return

        if config.sections["notifications"]["notification_popup_folder"]:
            core.notifications.show_download_notification(
                _("%(folder)s downloaded from %(user)s") % {
                    "user": user,
                    "folder": folderpath
                },
                title=_("Folder Downloaded")
            )

        if config.sections["transfers"]["afterfolder"]:
            try:
                execute_command(config.sections["transfers"]["afterfolder"], folderpath)
                log.add(_("Executed on folder: %s"), config.sections["transfers"]["afterfolder"])

            except Exception:
                log.add(_("Trouble executing on folder: %s"), config.sections["transfers"]["afterfolder"])

    def _download_finished(self, transfer, file_handle=None):

        core.transfers.close_file(file_handle, transfer)

        if transfer in self.download_requests:
            del self.download_requests[transfer]

        download_folder_path = transfer.path or self._get_default_download_folder(transfer.user)
        download_folder_path_encoded = encode_path(download_folder_path)
        download_basename = self._get_download_basename(transfer.filename, download_folder_path, avoid_conflict=True)
        download_file_path = os.path.join(download_folder_path, download_basename)

        try:
            if not os.path.isdir(download_folder_path_encoded):
                os.makedirs(download_folder_path_encoded)

            import shutil
            shutil.move(file_handle.name, encode_path(download_file_path))

        except OSError as error:
            log.add(
                _("Couldn't move '%(tempfile)s' to '%(file)s': %(error)s"), {
                    "tempfile": file_handle.name.decode("utf-8", "replace"),
                    "file": download_file_path,
                    "error": error
                }
            )
            self._abort_download(transfer, abort_reason="Download folder error")
            core.notifications.show_download_notification(
                str(error), title=_("Download Folder Error"), high_priority=True
            )
            return

        transfer.status = "Finished"
        transfer.current_byte_offset = transfer.size
        transfer.sock = None
        transfer.token = None

        core.statistics.append_stat_value("completed_downloads", 1)

        # Attempt to show notification and execute commands
        self._file_downloaded_actions(transfer.user, download_file_path)
        self._folder_downloaded_actions(transfer.user, transfer.path)

        finished = True
        events.emit("download-notification", finished)

        # Attempt to autoclear this download, if configured
        if not self._auto_clear_download(transfer):
            self._update_download(transfer)

        core.pluginhandler.download_finished_notification(transfer.user, transfer.filename, download_file_path)

        log.add_download(
            _("Download finished: user %(user)s, file %(file)s"), {
                "user": transfer.user,
                "file": transfer.filename
            }
        )

    def _auto_clear_download(self, download):

        if config.sections["transfers"]["autoclear_downloads"]:
            self._clear_download(download)
            return True

        return False

    def _update_download(self, transfer, update_parent=True):
        events.emit("update-download", transfer, update_parent)

    def check_download_timeouts(self, timeout):

        if not timeout or not self.download_requests:
            return

        abort_reason = "Connection timeout"
        current_time = time.time()
        need_update = False

        for transfer, start_time in self.download_requests.copy().items():
            if (current_time - start_time) >= timeout:
                core.transfers.transfer_timeout(transfer)
                self._abort_download(transfer, abort_reason=abort_reason, update_parent=False)  # TODO test this change

                need_update = True

        if need_update:
            events.emit("update-downloads")  # TODO test this change, consider only update specific user rows
            # self.check_download_queue()  # TODO consider

    def check_download_queue(self):

        statuslist_failed = ("Connection timeout", "Local file error", "Remote file error")

        for download in reversed(self.downloads):
            if download.status in statuslist_failed:
                # Retry failed downloads every 3 minutes

                self._abort_download(download, abort_reason=None)  # TODO consider, update_parent=False)
                self.get_file(download.user, download.filename, transfer=download)

            if download.status == "Queued":
                # Request queue position every 3 minutes

                core.send_message_to_peer(
                    download.user,
                    slskmessages.PlaceInQueueRequest(file=download.filename, legacy_client=download.legacy_attempt)
                )

    def _retry_download(self, transfer, bypass_filter=False):

        if transfer.status in ("Transferring", "Finished"):
            return

        user = transfer.user

        self._abort_download(transfer, abort_reason=None, update_parent=False)  # TODO  test change
        self.get_file(user, transfer.filename, transfer=transfer, bypass_filter=bypass_filter)

    def retry_downloads(self, downloads):

        num_downloads = len(downloads)

        for download in downloads:
            # Provide a way to bypass download filters in case the user actually wants a file.
            # To avoid accidentally bypassing filters, ensure that only a single file is selected,
            # and it has the "Filtered" status.

            bypass_filter = (num_downloads == 1 and download.status == "Filtered")
            self._retry_download(download, bypass_filter)

        events.emit("update-downloads")  # TODO test this change

    def retry_download_limits(self):

        need_update = False
        statuslist_limited = ("Too many files", "Too many megabytes")

        for download in reversed(self.downloads):
            if download.status in statuslist_limited or download.status.startswith("User limit of"):
                # Re-queue limited downloads every 12 minutes

                log.add_transfer("Re-queuing file %(filename)s from user %(user)s in download queue", {
                    "filename": download.filename,
                    "user": download.user
                })

                self._abort_download(download, abort_reason=None, update_parent=False)  # TODO test this change
                self.get_file(download.user, download.filename, transfer=download)

                need_update = True

        if need_update:
            events.emit("update-downloads")  # TODO test this change, consider only update specific user rows

    def _abort_download(self, download, abort_reason="Paused", update_parent=True):

        log.add_transfer(('Aborting download, user "%(user)s", filename "%(filename)s", token "%(token)s", '
                          'status "%(status)s"'), {
            "user": download.user,
            "filename": download.filename,
            "token": download.token,
            "status": download.status
        })

        download.legacy_attempt = False
        download.size_changed = False
        download.token = None
        download.queue_position = 0

        if download in self.download_requests:
            del self.download_requests[download]

        if download.sock is not None:
            core.queue.append(slskmessages.CloseConnection(download.sock))
            download.sock = None

        if download.file is not None:
            core.transfers.close_file(download.file, download)

            log.add_download(
                _("Download aborted, user %(user)s file %(file)s"), {
                    "user": download.user,
                    "file": download.filename
                }
            )

        if abort_reason:
            download.status = abort_reason

        events.emit("abort-download", download, abort_reason, update_parent)

    def abort_downloads(self, downloads, abort_reason="Paused"):

        for download in downloads:
            if download.status not in (abort_reason, "Finished"):
                self._abort_download(download, abort_reason=abort_reason, update_parent=False)

        events.emit("abort-downloads", downloads, abort_reason)

    def _clear_download(self, download, update_parent=True):

        self._abort_download(download, abort_reason=None)
        self.downloads.remove(download)

        events.emit("clear-download", download, update_parent)

    def clear_downloads(self, downloads=None, statuses=None, clear_deleted=False):

        if downloads is None:
            # Clear all downloads
            downloads = self.downloads

        for download in downloads.copy():
            if statuses and download.status not in statuses:
                continue

            if clear_deleted:
                if download.status != "Finished":
                    continue

                if core.transfers.get_complete_download_file_path(
                        download.user, download.filename, download.path, download.size):
                    continue

            self._clear_download(download, update_parent=False)

        events.emit("clear-downloads", downloads, statuses, clear_deleted)

    """ Filters """

    def update_download_filters(self):

        failed = {}
        outfilter = "(\\\\("
        download_filters = sorted(config.sections["transfers"]["downloadfilters"])
        # Get Filters from config file and check their escaped status
        # Test if they are valid regular expressions and save error messages

        for item in download_filters:
            dfilter, escaped = item
            if escaped:
                dfilter = re.escape(dfilter)
                dfilter = dfilter.replace("\\*", ".*")

            try:
                re.compile(f"({dfilter})")
                outfilter += dfilter

                if item is not download_filters[-1]:
                    outfilter += "|"

            except re.error as error:
                failed[dfilter] = error

        outfilter += ")$)"

        try:
            re.compile(outfilter)

        except re.error as error:
            # Strange that individual filters _and_ the composite filter both fail
            log.add(_("Error: Download Filter failed! Verify your filters. Reason: %s"), error)
            config.sections["transfers"]["downloadregexp"] = ""
            return

        config.sections["transfers"]["downloadregexp"] = outfilter

        # Send error messages for each failed filter to log window
        if not failed:
            return

        errors = ""

        for dfilter, error in failed.items():
            errors += f"Filter: {dfilter} Error: {error} "

        log.add(_("Error: %(num)d Download filters failed! %(error)s "), {"num": len(failed), "error": errors})

    """ Saving """

    def get_downloads(self):
        """ Get a list of downloads """
        return [
            [download.user, download.filename, download.path, download.status, download.size,
             download.current_byte_offset, download.file_attributes]
            for download in reversed(self.downloads)
        ]

    def save_downloads_callback(self, filename):
        json.dump(self.get_downloads(), filename, ensure_ascii=False)
