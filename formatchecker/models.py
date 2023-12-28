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
import difflib

from .llvm import parse_diff_segments


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
        # set up internal variables used by the property getters/setters
        self._patch_segments: list[Segment] = []

        # set up object
        self.filename = filename
        self._base_contents = base
        self._patch_contents = patch
        self.formatted_contents: list[str] | None = None
        self.format_segments: list[FormatSegment] = []
        self._calculate_patch_segments()

    @property
    def base_contents(self) -> list[str] | None:
        return self._base_contents

    @base_contents.setter
    def base_contents(self, base: list[str] | None):
        self._base_contents = base
        print("base %s patch %s" % (self._base_contents, self._patch_contents))
        self._calculate_patch_segments()

    @property
    def patch_contents(self) -> list[str] | None:
        return self._patch_contents

    @patch_contents.setter
    def patch_contents(self, patch: list[str] | None):
        self._patch_contents = patch
        self._calculate_patch_segments()

    @property
    def patch_segments(self) -> list[Segment]:
        """Read-only property that contains all the segments in the patched contents that are added or modified in
        comparison to the base content. If lines are deleted in the new content, those segments are ignored.
        Getting this attribute will raise a `RuntimeError` if there is no base or patch content, and the segments
        therefore could not have been calculated.
        """
        if self._base_contents is None or self._patch_contents is None:
            raise RuntimeError(
                "This File does not have base_contents or patch_contents, so no patch_segments are known"
            )
        return self._patch_segments

    def add_format_segment(self, start: int, end: int | None, format_contents: list[str]):
        """Add a format segment to this file. A format segment which part of the patched content
        needs to be reformated in order to be in compliance with the style."""
        self.format_segments.append(FormatSegment(start, end, format_contents))

    def set_formatted_contents(self, contents: list[str]):
        """Method to be used to store the output of the external format checker (clang-format or
        haiku-format)."""
        if self.patch_contents != contents:
            self.formatted_contents = contents

    def _calculate_patch_segments(self):
        """Internal method to calculate the segments that are inserted or modified in the patch in comparison to the
        base. Deletions are ignored.
        """
        # clear any previously calculated patch contents
        self._patch_segments.clear()
        if self._base_contents is None or self._patch_contents is None:
            # nothing to compare
            return

        diff = difflib.unified_diff(self._base_contents, self._patch_contents, fromfile='base/file',
                                    tofile='patch/file', n=0)
        segments = parse_diff_segments(diff)['file']
        for a_start, a_end, b_start, b_end in segments:
            if b_end is None:
                # The change is a deletion only, so there is no syntax to check in the modified file
                continue
            self._patch_segments.append(Segment(b_start, b_end))

    def __repr__(self):
        return "Gerrit file %s" % self.filename


class Change:
    """Represents a change in Gerrit, including a list of files"""
    def __init__(self, change_id: str, files: list[File]):
        self.change_id = change_id
        self.files = files

    def __repr__(self):
        return "Gerrit change %s" % self.change_id
