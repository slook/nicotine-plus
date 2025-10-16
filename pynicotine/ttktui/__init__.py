# SPDX-FileCopyrightText: 2026 Nicotine+ Contributors
# SPDX-License-Identifier: GPL-3.0-or-later

import os
import sys


def check_ttk_version(ttk_library_path):

    ttk_min_version = 48  # 0.47.3 or 0.48.1 or 0.49.0 or 0.50.0
    sys.path.insert(1, ttk_library_path)  # ../libs/pyTermTk

    print("Using %s executable: %s" % ("TTk", ttk_library_path))  # log.add(

    try:
        # Don't catch ImportError, just show the raw stack trace
        from TermTk import __version__ as TTk_version
        # from pynicotine.external.pyTermTk import TermTk as ttk

        if int(TTk_version.split(".")[1]) < ttk_min_version:
            raise ValueError

        print("Imported %(program)s %(version)s" % {"program": "TermTk", "version": TTk_version})

    except ValueError:
        return _("Cannot find %s, please install it.") % f"TermTk >= 0.{ttk_min_version}.0 in path '{ttk_library_path}'"

    print(_("Loaded %(program)s %(version)s") % {"program": "TTk", "version": TTk_version})
    return None


def run(ci_mode, isolated_mode):
    """Run Nicotine+ TTk "Terminal Toolkit" Text User Interface (TUI)."""

    error = check_ttk_version(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'external', 'pyTermTk'))

    if error:
        print(error)
        return 1

    from pynicotine.ttktui.application import Application

    if not os.isatty(os.sys.stdin.fileno()):
        print("Teletypewriter unavailable, cannot start TermTk TUI")

        if ci_mode:
            print("TermTk TUI initialized for CI tests...")
            from time import sleep
            sleep(6)
            print("No CI tests so not a failure, the end!")
            return 0

        print("Application running in headless mode, press Ctrl+C to quit.")
        return None

    return Application(ci_mode, isolated_mode).run()
