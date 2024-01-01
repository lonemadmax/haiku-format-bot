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
from dataclasses import dataclass
from enum import Enum, StrEnum, auto

from .llvm import parse_diff_segments


class Segment:
    """Represents a segment of a text file, with a start line and an optional end line.
    The segment is inclusive, meaning that if the segment has start 3 and end 5, that lines
    3, 4 and 5 are included.
    If the end is None, then the segment indicates an insertion point at the start line.
    """
    def __init__(self, start: int, end: int | None):
        if start < 1:
            raise ValueError("Start value must be 1 or higher")
        if end is not None:
            if end < 1:
                raise ValueError("End value must be 1 or higher")
            if end < start:
                raise ValueError("End value must be equal to or higher than start value")
        self._start = start
        self._end = end

    @property
    def start(self) -> int:
        return self._start

    @property
    def end(self) -> int | None:
        return self._end

    def format_range(self) -> str:
        """Format the segment as a range. If the segment is not a range but an insertion point,
        this will raise a `ValueError`
        """
        if self.end is None:
            raise ValueError("Segment does not have an endpoint and is not a range")
        return "%i:%i" % (self.start, self.end)

    def __eq__(self, other):
        if isinstance(other, Segment):
            return self.start == other.start and self.end == other.end
        return False

    def __repr__(self):
        try:
            return "Segment %s" % self.format_range()
        except ValueError:
            return "Segment %i (insert point)" % self.start


class ReformatType(Enum):
    INSERTION = auto()
    MODIFICATION = auto()
    DELETION = auto()


class FormatSegment(Segment):
    """Represents a reformatted segment. The segment can be """
    def __init__(self, start: int, end: int | None, formatted_content: list[str]):
        if end is None and len(formatted_content) == 0:
            raise ValueError(
                "When creating an insertion segment (where end is None), formatted_content must have 1 or more elements"
            )

        super().__init__(start, end)
        self._formatted_content = formatted_content

    @property
    def formatted_content(self):
        """Content that replaces the existing content at the range of this segment. If the value is an empty list, it
        means it is a deletion segment.
        """
        return self._formatted_content

    @property
    def reformat_type(self) -> ReformatType:
        """Get the type of reformatting in this format segment.
        `ReformatType.INSERT` means that this modification inserts new content. The start point represents the insert
        point of the new formatted content.
        For example, this can happen if the style guide mandates a newline after a certain
        statement or construct. The original content is not modified, but something is added.
        Insert segments will not have an end point.
        `ReformatType.MODIFICATION` means that the contents at the range of the segment needs to be replaced
        with the lines in formatted_content.
        Modification segments will have a start and an end point. The formatted content can have
        a different number of lines as the original range.
        `ReformatType.DELETION` means that the range of lines need to be removed.
        For example, this can happen if the input has more newlines than the style guide mandates.
        """
        if self.end is None:
            return ReformatType.INSERTION
        elif len(self.formatted_content) == 0:
            return ReformatType.DELETION
        else:
            return ReformatType.MODIFICATION

    def __eq__(self, other):
        if isinstance(other, FormatSegment):
            return super(Segment).__eq__(other) and self.formatted_content == other.formatted_content
        return False

    def __repr__(self):
        match self.reformat_type:
            case ReformatType.INSERTION:
                operation = "(insert)"
            case ReformatType.MODIFICATION:
                operation = "(modification)"
            case ReformatType.DELETION:
                operation = "(deletion)"
            case _:
                raise RuntimeError("Unsupported operation: %s", self.reformat_type)
        return "%s %s" % (super().__repr__(), operation)


class File:
    """Represents a file in a Gerrit change, including its content"""
    def __init__(self, filename: str, base: list[str] | None = None, patch: list[str] | None = None):
        # set up internal variables used by the property getters/setters
        self._patch_segments: list[Segment] = []

        # set up object
        self.filename = filename
        self._base_contents = base
        self._patch_contents = patch
        self._formatted_contents: list[str] | None = None
        self._format_segments: list[FormatSegment] = []
        self._calculate_patch_segments()

    @property
    def base_contents(self) -> list[str] | None:
        return self._base_contents

    @base_contents.setter
    def base_contents(self, base: list[str] | None):
        self._base_contents = base
        self._calculate_patch_segments()

    @property
    def patch_contents(self) -> list[str] | None:
        return self._patch_contents

    @patch_contents.setter
    def patch_contents(self, patch: list[str] | None):
        self._patch_contents = patch
        self._calculate_patch_segments()

    @property
    def formatted_contents(self) -> list[str] | None:
        return self._formatted_contents

    @formatted_contents.setter
    def formatted_contents(self, contents: list[str] | None):
        if self._patch_contents != contents:
            self._formatted_contents = contents
        self._calculate_formatted_segments()

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

    @property
    def format_segments(self) -> list[FormatSegment]:
        """Read-only property that contains all the segments in the patched content that have been reformatted by
        the formatter.
        Getting this attribute will raise a `RuntimeError` if there is no patch or formatted content, which means
        there are no segments calculated.
        """
        if self._patch_contents is None or self._formatted_contents is None:
            raise RuntimeError(
                "This File does not have patch_contents or format_contents, so no format_segments are known"
            )
        return self._format_segments

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
        try:
            segments = parse_diff_segments(diff)['file']
        except KeyError:
            # there are no differences
            return
        for a_start, a_end, b_start, b_end in segments:
            if b_end is None:
                # The change is a deletion only, so there is no syntax to check in the modified file
                continue
            self._patch_segments.append(Segment(b_start, b_end))

    def _calculate_formatted_segments(self):
        """Compare the original contents with the reformatted, and annotate the modified segments"""
        self._format_segments.clear()
        if self._patch_contents is None or self._formatted_contents is None:
            # Nothing to compare
            return
        diff = difflib.unified_diff(self._patch_contents, self._formatted_contents, fromfile='patch/file',
                                    tofile='formatted/file', n=0)
        segments = parse_diff_segments(diff)['file']
        for a_start, a_end, b_start, b_end in segments:
            if not b_end:
                # The change is a deletion, so no new content is expected.
                self._format_segments.append(FormatSegment(a_start, a_end, []))
            else:
                self._format_segments.append(FormatSegment(a_start, a_end, self._formatted_contents[b_start-1:b_end]))

    def __repr__(self):
        return "Gerrit file %s" % self.filename


class Change:
    """Represents a change in Gerrit, including a list of files"""
    def __init__(self, change_id: str, files: list[File]):
        self.change_id = change_id
        self.files = files

    def __repr__(self):
        return "Gerrit change %s" % self.change_id


# Gerrit specific data models
class SideEnum(StrEnum):
    """Gerrit enum of valid values for the 'side' member of a (Robot)CommentInput, to determine on which side of the
    diff the comment is placed.
    """
    REVISION = auto()
    PARENT = auto()


@dataclass
class CommentRange:
    """Gerrit object that represents a 'comment range' on a Change. It is used together with ReviewInput.
    See: https://review.haiku-os.org/Documentation/rest-api-changes.html#comment-range
    """
    start_line: int
    start_character: int
    end_line: int
    end_character: int


@dataclass
class FixReplacementInfo:
    """https://review.haiku-os.org/Documentation/rest-api-changes.html#fix-replacement-info"""
    path: str
    range: CommentRange
    replacement: str


@dataclass
class FixSuggestion:
    """https://review.haiku-os.org/Documentation/rest-api-changes.html#fix-suggestion-info"""
    description: str
    replacements: list[FixReplacementInfo]
    fix_id: str | None = None


@dataclass
class CommentInput:
    """Gerrit object that represents a comment on a Change. It is used together with ReviewInput."""
    id: str | None = None
    path: str | None = None
    side: SideEnum | None = None
    line: int | None = None
    range: CommentRange | None = None
    in_reply_to: str | None = None
    updated: str | None = None
    message: str | None = None
    tag: str | None = None
    unresolved: bool | None = None


@dataclass
class RobotCommentInput:
    """Gerrit object that represents a 'robot comment' on a Change. It is used together with ReviewInput.
    Note that the order of the values is different, because Python requires the values without a default to
    be before any values with a default.
    See: https://review.haiku-os.org/Documentation/rest-api-changes.html#robot-comment-input
    """
    path: str
    robot_id: str
    robot_run_id: str
    side: SideEnum | None = None
    line: int | None = None
    range: CommentRange | None = None
    in_reply_to: str | None = None
    message: str | None = None
    url: str | None = None
    properties: dict[str, str] | None = None
    fix_suggestions: list[FixSuggestion] | None = None


class DraftsEnum(StrEnum):
    """Gerrit enum of valid values to determine what to do with draft comments when submitting a ReviewInput.
    When unset, the default is KEEP.
    """
    PUBLISH = auto()
    PUBLISH_ALL_REVISIONS = auto()
    KEEP = auto()


class NotifyEnum(StrEnum):
    """Gerrit enum of valid values to determine who gets notified when a review is published. It is used when
    submitting a ReviewInput.
    When unset, the default is ALL.
    """
    NONE = auto()
    OWNER = auto()
    OWNER_REVIEWERS = auto()
    ALL = auto()


@dataclass
class ReviewInput:
    """Gerrit object that represents a 'review' on a Change
    See: https://review.haiku-os.org/Documentation/rest-api-changes.html#review-input
    """
    message: str | None = None
    tag: str | None = "autogenerated:experimental-formatting-bot"
    labels: dict[str, int] | None = None
    comments: dict[str, list[CommentInput]] | None = None
    robot_comments: dict[str, list[RobotCommentInput]] | None = None
    drafts: DraftsEnum | None = None
    draft_ids_to_publish: list[str] | None = None
    notify: NotifyEnum | None = None
    # notify_details = list[NotifyInfo] | None
    omit_duplicate_comments: bool | None = None
    on_behalf_of: str | None = None
    # reviewers = list[ReviewerInput] | None
    ready: bool | None = None
    work_in_progress: bool | None = None
    # add_to_attention_set = list[AttentionSetInput] | None
    # remove_from_attention_set = list[AttentionSetInput] | None
    ignore_automatic_attention_set_rules: bool | None = None
