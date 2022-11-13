# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

import os
import unittest

from pynicotine.config import config
from pynicotine.core import core

SHARES_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), ".sharedfiles")


class SharesTest(unittest.TestCase):

    def setUp(self):

        config.data_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "dbs")
        config.filename = os.path.join(config.data_dir, "temp_config")

        config.load_config()
        config.sections["transfers"]["shared"] = [("Shares", SHARES_DIR)]

        core.init_components()
        core.shares.rescan_shares(use_thread=False)

    def tearDown(self):
        core.shares.close_shares(core.shares.share_dbs)

    def test_shares_scan(self):
        """ Test a full shares scan """

        # Verify that modification time was saved for shares folder
        self.assertIn(SHARES_DIR, list(core.shares.share_dbs["mtimes"]))

        # Verify that shared files were added
        self.assertIn(['dummy_file', 0, None, None], core.shares.share_dbs["files"]["Shares"])
        self.assertIn(
            ['nicotinetestdata.mp3', 80919, (128, 0, 44100, None), 5], core.shares.share_dbs["files"]["Shares"])
        self.assertIn(['nicotinevbr.mp3', 36609, (32, 1, 44100, None), 9], core.shares.share_dbs["files"]["Shares"])

        # Verify that expected folder is empty
        self.assertEqual(len(core.shares.share_dbs["files"]["Shares\\folder2"]), 0)

        # Verify that search index was updated
        word_index = core.shares.share_dbs["wordindex"]
        nicotinetestdata_indexes = list(word_index["nicotinetestdata"])
        ogg_indexes = list(word_index["ogg"])

        self.assertEqual(set(word_index), set(
            ['nicotinetestdata', 'ogg', 'mp3', 'shares', 'file', 'dummy', 'folder1',
             'folder2', 'nothing', 'something', 'test', 'nicotinevbr']
        ))
        self.assertEqual(len(nicotinetestdata_indexes), 2)
        self.assertEqual(len(ogg_indexes), 1)

        # File ID associated with word "ogg" should return our nicotinetestdata.ogg file
        self.assertIn(ogg_indexes[0], nicotinetestdata_indexes)
        self.assertEqual(core.shares.share_dbs["fileindex"][str(ogg_indexes[0])][0], 'Shares\\nicotinetestdata.ogg')

    def test_hidden_file_folder_scan(self):
        """ Test that hidden files and folders are excluded """

        # Check folders
        mtimes = list(core.shares.share_dbs["mtimes"])

        self.assertNotIn(os.path.join(SHARES_DIR, ".abc"), mtimes)
        self.assertNotIn(os.path.join(SHARES_DIR, ".xyz"), mtimes)
        self.assertIn(os.path.join(SHARES_DIR, "folder1"), mtimes)
        self.assertIn(os.path.join(SHARES_DIR, "folder2"), mtimes)
        self.assertNotIn(os.path.join(SHARES_DIR, "folder2", ".poof"), mtimes)
        self.assertIn(os.path.join(SHARES_DIR, "folder2", "test"), mtimes)
        self.assertIn(os.path.join(SHARES_DIR, "something"), mtimes)

        # Check files
        files = core.shares.share_dbs["files"]["Shares"]

        self.assertNotIn([".abc_file", 0, None, None], files)
        self.assertNotIn([".hidden_file", 0, None, None], files)
        self.assertNotIn([".xyz_file", 0, None, None], files)
        self.assertIn(["dummy_file", 0, None, None], files)
        self.assertEqual(len(files), 4)
