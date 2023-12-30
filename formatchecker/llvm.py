#!/usr/bin/env python3
#
# The code in this file is based on `clang-format-diff.py` which is part of the
# LLVM project. Therefore, this file is licensed under the original license.
#
# Adapted by Niels S. Reedijk <niels.reedijk@gmail.com> for the Haiku project.
#
# Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
# See https://llvm.org/LICENSE.txt for license information.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception

"""
This module contains various algorithms that are based on the `clang-format-diff.py` code that
is part of LLVM. The original logic has been split into various utility functions, and has
been enhanced in places.
"""
import re
import subprocess
from io import StringIO
from typing import Optional, Iterator

FORMAT_COMMAND = 'haiku-format'


def parse_diff_segments(diff: Iterator[str]) -> dict[str, list[tuple[int, Optional[int], int, Optional[int]]]]:
    """Parse a diff file, and return a tuple with all change segments.

    The input is a unified diff, split up as an iterator that iterates over lines. The input can be the output of
    the `difflib.unified_diff()` function, or a file handle that opens a file in text mode.

    The return value is a dict with a list of tuples. The key in the dict is the filename of the original file.
    Each tuple in the list contains 4 elements:
     - a_start: the starting line in the original file that is modified.
     - a_end: the end line in the original file that is modified. If the modification only adds lines, a_end is `None`
     - b_start: the starting line for changes in the modified file
     - b_end: the end line with modifications. If the modifications only removes lines, this is set to `None`
    If parsing was unsuccessful, the returned dict is empty.
    """
    filename = None
    lines_by_file = {}
    for line in diff:
        # find a filename
        match = re.search(r"^\+\+\+ (.*?/){%s}(\S*)" % "1", line)
        if match:
            filename = match.group(2)
        if filename is None:
            continue

        # fetch all the values
        match = re.search(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))?", line)
        if match:
            a_start = int(match.group(1))
            a_end = a_start
            line_count = 1
            if match.group(2):
                line_count = int(match.group(2))
            if line_count != 0:
                a_end += line_count - 1
            else:
                # In case the new file only adds line(s) and not modifies anything, the line count is 0.
                a_end = None

            b_start = int(match.group(3))
            b_end = b_start
            line_count = 1
            if match.group(4):
                line_count = int(match.group(4))
                # The input is something like
                #
                # @@ -1, +0,0 @@
                #
                # which means no lines were added.
                if line_count == 0:
                    b_end = None
            # Also format lines range if line_count is 0 in case of deleting
            # surrounding statements.
            if line_count != 0:
                b_end += line_count - 1
            lines_by_file.setdefault(filename, []).extend(
                [(a_start, a_end, b_start, b_end)]
            )
    return lines_by_file


def run_clang_format(contents: list[str], segment_ranges: list[str]) -> list[str]:
    """Run clang-format over a contents, limited to a set of ranges. The output of clang-format is returned as a list
    of lines
    """
    command = [FORMAT_COMMAND]
    # TODO see notes: clang-format seems to resort includes even outside of the changed segments
    # command.append('-sort-includes=0')
    for segment in segment_ranges:
        command.extend(['-lines', segment])
    try:
        p = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=None,
            stdin=subprocess.PIPE,
            universal_newlines=True,
        )
    except OSError as e:
        # Give the user more context when clang-format isn't
        # found/isn't executable, etc.
        raise RuntimeError(
            'Failed to run "%s" - %s"' % (" ".join(command), e.strerror)
        )

    stdout, stderr = p.communicate("".join(contents))
    if p.returncode != 0:
        raise RuntimeError(
            'Could not run %s. Error output:\n%s' % (" ".join(command), stderr)
        )
    return StringIO(stdout).readlines()
