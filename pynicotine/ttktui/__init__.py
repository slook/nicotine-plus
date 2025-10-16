# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys


def check_ttk_version():

    ttk_min_version = 48
    ttk_library_path = os.path.join(sys.path[0], 'pynicotine', 'external', 'pyTermTk')

    sys.path.insert(1, ttk_library_path)  # ../libs/pyTermTk

    try:
        if not os.path.isdir(os.path.join(ttk_library_path, 'TermTk')):
            raise OSError

        print("Using %s executable: %s" % ("TTk", os.path.join(ttk_library_path, 'TermTk')))  # log.add(

        # Don't catch ImportError, just show the raw stack trace
        from TermTk import __version__ as TTk_version

        if int(TTk_version.split(".")[1]) < ttk_min_version:  # 0.47.3 or 0.48.1 or 0.49.0
            raise ValueError

        print(_("Loaded %(program)s %(version)s") % {"program": "TTk", "version": TTk_version})

    except (OSError, ValueError):
        return _("Cannot find %s, please install it.") % f"TermTk >= 0.{ttk_min_version}.0 in path '{ttk_library_path}'"

    return None


def run(ci_mode):
    """Run Nicotine+ TTk "Terminal Toolkit" Text User Interface (TUI)."""

    error = check_ttk_version()

    if error:
        print(error)
        return 1

    from pynicotine.ttktui.application import Application
    return Application(ci_mode).run()
