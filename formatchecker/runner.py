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
        self.segments: list[PatchSegment] = []

    def add_segment(self, start: int, end: int):
        self.segments.append(PatchSegment(start, end))

    def set_formatted_contents(self, contents: str):
        if self.original_contents != contents:
            self.formatted_contents = contents

    def __repr__(self):
        segments = []
        for segment in self.segments:
            segments.append(segment.format_range())
        return "%s [%i segments] %s" % (self.filename, len(self.segments), ",".join(segments))


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
            modified_file.add_segment(start_line, end_line)


def _run_clang_format(input_file: RevisionFile):
    """Run clang-format for the relevant segments of the input file and return the modified file"""
    command = [FORMAT_COMMAND]
    for segment in input_file.segments:
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
