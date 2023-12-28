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
import difflib
import re
import subprocess
from io import StringIO
from typing import TextIO, Optional, Iterator

from .models import File

FORMAT_COMMAND = 'clang-format-16'
EXTENSION_PATTERN = (r".*\.(?:cpp|cc|c\+\+|cxx|cppm|ccm|cxxm|c\+\+m|c|cl|h|hh|hpp"
                     r"|hxx|m|mm|inc|js|ts|proto|protodevel|java|cs|json|s?vh?)")


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


def _parse_input_diff(files: dict[str, File], diff: TextIO):
    """Parses the input diff and formats a list of files and patch segments"""
    patch_segments = parse_diff_segments(diff)
    for filename, segments in patch_segments.items():
        try:
            modified_file = files[filename]
        except KeyError:
            print("Log: diff file contains diff for %s but not part of files selected for change" % filename)
            continue

        for a_start, a_end, b_start, b_end in segments:
            if b_end is None:
                # The change is a deletion only, so there is no syntax to check in the modified file
                continue
            modified_file.add_patch_segment(b_start, b_end)


def _run_clang_format(input_file: File):
    """Run clang-format for the relevant segments of the input file and save the modified file"""
    command = [FORMAT_COMMAND]
    for segment in input_file.patch_segments:
        command.extend(['-lines', segment.format_range()])
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

    stdout, stderr = p.communicate("".join(input_file.patch_contents))
    if p.returncode != 0:
        raise RuntimeError(
            'Could not run %s. Error output:\n%s' % (" ".join(command), stderr)
        )
    input_file.set_formatted_contents(StringIO(stdout).readlines())


def _split_format_segments(input_file: File):
    """Compare the original contents with the reformatted, and annotate the modified segments"""
    if input_file.formatted_contents is None:
        print("Cannot find differences, returning.")
        return
    diff = difflib.unified_diff(input_file.patch_contents, input_file.formatted_contents, fromfile='patch/file',
                                tofile='formatted/file', n=0)
    segments = parse_diff_segments(diff)['file']
    for a_start, a_end, b_start, b_end in segments:
        if not b_end:
            # The change is a deletion, so no new content is expected.
            input_file.add_format_segment(a_start, a_end, [])
        else:
            input_file.add_format_segment(a_start, a_end, input_file.formatted_contents[b_start-1:b_end])
