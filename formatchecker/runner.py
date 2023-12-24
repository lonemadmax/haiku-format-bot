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
import os
import re
import subprocess
from typing import TextIO

FORMAT_COMMAND = 'clang-format-16'
EXTENSION_PATTERN = (r".*\.(?:cpp|cc|c\+\+|cxx|cppm|ccm|cxxm|c\+\+m|c|cl|h|hh|hpp"
                     r"|hxx|m|mm|inc|js|ts|proto|protodevel|java|cs|json|s?vh?)")


class PatchSegment:
    def __init__(self, start: int, end: int):
        self.start = start
        self.end = end

    def format_range(self) -> str:
        return "%i:%i" % (self.start, self.end)


class ModifiedFile:
    def __init__(self, filename: str):
        self.filename = filename
        self.segments: list[PatchSegment] = []

    def add_segment(self, start: int, end: int):
        self.segments.append(PatchSegment(start, end))

    def __repr__(self):
        return self.filename


def _parse_input_diff(diff: TextIO) -> list[ModifiedFile]:
    """Parses the input diff and formats a list of files and patch segments"""
    modified_file = None
    processed_files = []
    for line in diff.readlines():
        match = re.search(r"^\+\+\+ (.*?/){%s}(\S*)" % "1", line)
        if match:
            modified_file = ModifiedFile(match.group(2))
            processed_files.append(modified_file)
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

    # remove any files that do not have modification segments
    return list(filter(lambda f: len(f.segments) > 0, processed_files))


def _run_clang_format(input_file: ModifiedFile, tree: str) -> str:
    """Run clang-format for the relevant segments of the input file and return the modified file"""
    command = [FORMAT_COMMAND, os.path.join(tree, input_file.filename)]
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

    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(
            'Could not run %s. Error output:\n%s' % (" ".join(command), stderr)
        )
    return stdout
