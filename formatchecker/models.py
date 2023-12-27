#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
"""
This module contains the model classes that are shared between the various modules of this tool.
"""


class Segment:
    """Represents a segment of a text file, with a start line and an optional end line.
    The segment is inclusive, meaning that if the segment has start 3 and end 5, that lines
    3, 4 and 5 are included.
    If the end is None, then the segment indicates an insertion point at the start line.
    """
    def __init__(self, start: int, end: int | None):
        self.start = start
        self.end = end

    def format_range(self) -> str:
        """Format the segment as a range. If the segment is not a range but an insertion point,
        this will raise a `ValueError`
        """
        if self.end is None:
            raise ValueError("Segment does not have an endpoint and is not a range")
        return "%i:%i" % (self.start, self.end)

    def __repr__(self):
        try:
            return "Segment %s" % self.format_range()
        except ValueError:
            return "Segment %i (insert point)" % self.start


class FormatSegment(Segment):
    """Represents a reformatted segment. The segment can be """
    def __init__(self, start: int, end: int | None, formatted_content: list[str]):
        super().__init__(start, end)
        self.formatted_content = formatted_content

    def is_insert(self):
        """Returns true if the segment is an insert segment, which means that the start point
        represents the insert point of the new formatted content.
        For example, this can happen if the style guide mandates a newline after a certain
        statement or construct. The original content is not modified, but something is added.
        Insert segments will not have an end point.
        """
        return True if self.end is None else False

    def is_modification(self):
        """Returns true if the segment is a modification segment, which means that the contents
        at the range of the segment needs to be replaced with the lines in formatted_content.
        Modification segments will have a start and an end point. The formatted content can have
        a different number of lines as the original range.
        """
        return True if not self.is_insert() and not self.is_delete() else False

    def is_delete(self):
        """Returns true if the segment is a deletion segment, which means that the range of lines
        need to be removed.
        For example, this can happen if the input has more newlines than the style guide mandates.
        """
        return True if len(self.formatted_content) == 0 else False

    def __repr__(self):
        operation = "(modification)"
        if self.is_delete():
            operation = "(deletion)"
        elif self.is_insert():
            operation = "(insert)"
        return "%s %s" % (super().__repr__(), operation)


class File:
    """Represents a file in a Gerrit change, including its content"""
    def __init__(self, filename: str, base: list[str] | None, patch: list[str] | None):
        self.filename = filename
        self.base_contents = base
        self.patch_contents = patch
        self.formatted_contents: list[str] | None = None
        self.patch_segments: list[Segment] = []
        self.format_segments: list[FormatSegment] = []

    def add_patch_segment(self, start: int, end: int):
        """Add a patch segment to this file. A patch segment is a marker which part of the
        patched content is a modification in comparison to the base content."""
        self.patch_segments.append(Segment(start, end))

    def add_format_segment(self, start: int, end: int | None, format_contents: list[str]):
        """Add a format segment to this file. A format segment which part of the patched content
        needs to be reformated in order to be in compliance with the style."""
        self.format_segments.append(FormatSegment(start, end, format_contents))

    def set_formatted_contents(self, contents: list[str]):
        """Method to be used to store the output of the external format checker (clang-format or
        haiku-format)."""
        if self.patch_contents != contents:
            self.formatted_contents = contents

    def __repr__(self):
        return "Gerrit file %s" % self.filename


class Change:
    """Represents a change in Gerrit, including a list of files"""
    def __init__(self, change_id: str, files: list[File]):
        self.change_id = change_id
        self.files = files

    def __repr__(self):
        return "Gerrit change %s" % self.change_id
