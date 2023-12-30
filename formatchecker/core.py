#
# Copyright 2023 Haiku, Inc. All rights reserved.
# Distributed under the terms of the MIT License.
#
# Authors:
#  Niels Sascha Reedijk, niels.reedijk@gmail.com
#
"""
This module contains the core high-level objects and functions that are used to fetch a change,
reformat it, and publish those changes back to Gerrit.
"""
import dataclasses
import datetime
import json
import logging
import re
import sys

from .gerrit import Context
from .models import Change, ReviewInput, FixSuggestion, FixReplacementInfo, CommentRange, CommentInput
from .llvm import run_clang_format

EXTENSION_PATTERN = (r"^.*\.(?:cpp|cc|c\+\+|cxx|cppm|ccm|cxxm|c\+\+m|c|cl|h|hh|hpp"
                     r"|hxx|m|mm|inc|js|ts|proto|protodevel|java|cs|json|s?vh?)$")


def reformat_change(gerrit_url:str, change_id: int | str):
    """Function to fetch a change, reformat it, and publish the improvements to Gerrit"""
    logger = logging.getLogger("core")
    ctx = Context(gerrit_url)
    if isinstance(change_id, int):
        # convert a change number to an id
        change_id = ctx.get_change_id_from_number(change_id)
    change = ctx.get_change(change_id)
    for f in change.files:
        if not re.match(EXTENSION_PATTERN, f.filename, re.IGNORECASE):
            logger.info("Ignoring %s because it does not seem to be a file that `clang-format` can handle" % f.filename)
            continue
        if f.patch_contents is None:
            logger.info("Skipping %s because the file is deleted in the patch" % f.filename)
            continue
        segments = []
        for segment in f.patch_segments:
            segments.append(segment.format_range())
        reformatted_content = run_clang_format(f.patch_contents, segments)
        f.formatted_contents = reformatted_content
        if f.formatted_contents is None:
            logger.info("%s: no reformats" % f.filename)
        else:
            logger.info("%s: %i segment(s) reformatted" % (f.filename, len(f.format_segments)))

    review_input = _change_to_review_input(change)
    output = _review_input_as_pretty_json(review_input)
    with open("review.json", "wt") as f:
        f.write(output)
    url = "%sa/changes/%s/revisions/current/review" % (gerrit_url, change_id)
    logger.info("POST the contents of review.json to: %s", url)


def _change_to_review_input(change: Change) -> ReviewInput:
    """Internal function that converts a change into a ReviewInput object that can be pushed to Gerrit"""
    comments: dict[str, list[CommentInput]] = {}
    run_id = str(datetime.datetime.now())
    for f in change.files:
        if f.formatted_contents is None or len(f.format_segments) == 0:
            continue
        for segment in f.format_segments:
            end = segment.end
            if end is None:
                end = segment.start
            # As per the documentation, set the end point to character 0 of the next line to select all lines
            # between start_line and end_line (excluding any content of end_line)
            # https://review.haiku-os.org/Documentation/rest-api-changes.html#comment-range
            comment_range = CommentRange(segment.start, 0, end + 1, 0)
            message = "Suggestion from `haiku-format`:\n```c++\n%s\n```" % "".join(segment.formatted_content)
            comments.setdefault(f.filename, []).extend([CommentInput(
                message=message, range=comment_range
            )])

    if len(comments) == 0:
        message = "Experimental `haiku-format` bot: no formatting changes suggested for this commit."
    else:
        message = ("Experimental `haiku-format` bot: some formatting changes suggested. Note that this bot is "
                   "experimental and the suggestions may not be correct. There is a known issue with changes "
                   "in header files: `haiku-format` does not yet correctly output the column layout of the contents "
                   "of classes.\n\nYou can see and apply the suggestions by running `haiku-format` in your local "
                   "repository.")

    return ReviewInput(message=message, comments=comments)


def _review_input_as_pretty_json(input: ReviewInput):
    """Internal function that converts a ReviewInput document into json that can be sent to Gerrit.
    Since the ReviewInput is structured as a dataclass, it can be easily converted into a dict. If the Gerrit
    API states something is an optional value, then the classes allow None. When generating the JSON, these unset
    optional values will be filtered out (otherwise they will be sent added as null values in the JSON, which is
    semantically different than an optional value).
    """
    def remove_empty_value(_d):
        for key, value in list(_d.items()):
            if isinstance(value, dict):
                remove_empty_value(value)
            elif isinstance(value, list):
                for list_value in value:
                    if isinstance(list_value, dict):
                        remove_empty_value(list_value)
            elif value is None:
                del _d[key]

    d = dataclasses.asdict(input)
    remove_empty_value(d)
    return json.dumps(d, indent=4)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(
        prog="format-check",
        description="Checks the formatting of a patch on Haiku's Gerrit instance and publishes reformats if necessary")
    parser.add_argument('change_number', type=int)
    args = parser.parse_args()
    logging.basicConfig(stream=sys.stdout, level=logging.INFO)
    reformat_change("https://review.haiku-os.org/", args.change_number)
