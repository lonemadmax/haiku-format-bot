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
This module has as input a unified diff, reformats all the lines touched by
diff, and then if necessary, provide the improvements to the modified blocks.
"""
import re
import subprocess
from typing import TextIO, Optional

FORMAT_COMMAND = 'clang-format-16'
EXTENSION_PATTERN = (r".*\.(?:cpp|cc|c\+\+|cxx|cppm|ccm|cxxm|c\+\+m|c|cl|h|hh|hpp"
                     r"|hxx|m|mm|inc|js|ts|proto|protodevel|java|cs|json|s?vh?)")


class PatchSegment:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def format_range(self) -> str:
        return "%i:%i" % (self.start, self.end)

    def __repr__(self):
        return self.format_range()


class RevisionFile:
    def __init__(self, filename: str, contents: str):
        self.filename = filename
        self.original_contents = contents
        self.formatted_contents: Optional[str] = None
        self.patch_segments: list[PatchSegment] = []

    def add_patch_segment(self, start: int, end: int):
        self.patch_segments.append(PatchSegment(start, end))

    def set_formatted_contents(self, contents: str):
        if self.original_contents != contents:
            self.formatted_contents = contents

    def __repr__(self):
        segments = []
        for segment in self.patch_segments:
            segments.append(segment.format_range())
        return "%s [%i segments] %s" % (self.filename, len(self.patch_segments), ",".join(segments))


def _parse_diff(diff: list[str]) -> dict[str, list[tuple[int, Optional[int], int, Optional[int]]]]:
    """Parse a diff file, and return a tuple with all change segments.

    The input is a unified diff, split up as a list of lines.

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


def _parse_input_diff(files: dict[str, RevisionFile], diff: TextIO):
    """Parses the input diff and formats a list of files and patch segments"""
    modified_file: Optional[RevisionFile] = None
    for line in diff.readlines():
        match = re.search(r"^\+\+\+ (.*?/){%s}(\S*)" % "1", line)
        if match:
            try:
                modified_file = files[match.group(2)]
            except KeyError:
                print("Log: diff file contains diff for %s but not part of files selected for change" % match.group(2))
                continue
        if modified_file is None:
            continue

        # check if the file matches the expected filename extension
        if not re.match("^%s$" % EXTENSION_PATTERN, modified_file.filename, re.IGNORECASE):
            continue

        # find modified segments
        match = re.search(r"^@@.*\+(\d+)(?:,(\d+))?", line)
        if match:
            start_line = int(match.group(1))
            line_count = 1
            if match.group(2):
                line_count = int(match.group(2))
                # The input is something like
                #
                # @@ -1, +0,0 @@
                #
                # which means no lines were added.
                if line_count == 0:
                    continue
            # Also format lines range if line_count is 0 in case of deleting
            # surrounding statements.
            end_line = start_line
            if line_count != 0:
                end_line += line_count - 1
            modified_file.add_patch_segment(start_line, end_line)


def _run_clang_format(input_file: RevisionFile):
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

    stdout, stderr = p.communicate(input_file.original_contents)
    if p.returncode != 0:
        raise RuntimeError(
            'Could not run %s. Error output:\n%s' % (" ".join(command), stderr)
        )
    input_file.set_formatted_contents(stdout)
